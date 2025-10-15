from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_core.tools import tool
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from pathlib import Path
import json, hashlib
from langsmith import traceable
from langchain_core.documents import Document

load_dotenv()

INDEX_ROOT = Path(".indices")
INDEX_ROOT.mkdir(exist_ok=True)

#get youtube transcript
@traceable(name="get_youtube_transcript")
def get_youtube_transcript(video_id:str):

    try:
        # Fetch transcript directly (returns FetchedTranscriptSnippet objects)
        transcript_snippets = YouTubeTranscriptApi().fetch(video_id, languages=['en'])

        # Flatten into plain text
        text = " ".join(snippet.text for snippet in transcript_snippets)

    except TranscriptsDisabled:
        text = "No captions available for this video."
        return text
    
    return text



@traceable(name="split_documents")
def split_documents(docs, chunk_size=500, chunk_overlap=70):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)

@traceable(name="build_vectorstore")
def build_vectorstore(splits, embed_model_name: str):
    emb = OpenAIEmbeddings(model=embed_model_name)
    return FAISS.from_documents(splits, emb)

# ----------------- cache key / fingerprint -----------------
def _text_fingerprint(text: str) -> dict:
    """
    Generate a fingerprint (unique hash) for a text string.
    Useful for caching or indexing based on text content.
    """
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return {
        "sha256": h.hexdigest(),
        "length": len(text)
    }


def _index_key(text: str, chunk_size: int, chunk_overlap: int, embed_model_name: str) -> str:
    meta = {
        "text_fingerprint": _text_fingerprint(text),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embedding_model": embed_model_name,
        "format": "v1",
    }
    return hashlib.sha256(json.dumps(meta, sort_keys=True).encode("utf-8")).hexdigest()

# ----------------- explicitly traced load/build runs -----------------
@traceable(name="load_index", tags=["index"])
def load_index_run(index_dir: Path, embed_model_name: str):
    emb = OpenAIEmbeddings(model=embed_model_name)
    return FAISS.load_local(
        str(index_dir),
        emb,
        allow_dangerous_deserialization=True
    )

@traceable(name="build_index", tags=["index"])
def build_index_run(text: str, index_dir: Path, chunk_size: int, chunk_overlap: int, embed_model_name: str):
    docs = [Document(page_content=text)] 
    splits = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    vs = build_vectorstore(splits, embed_model_name)
    index_dir.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(index_dir))
    (index_dir / "meta.json").write_text(json.dumps({
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embedding_model": embed_model_name,
    }, indent=2))
    return vs

# ----------------- dispatcher -----------------
def load_or_build_index(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 70,
    embed_model_name: str = "text-embedding-3-small",
    force_rebuild: bool = False,
):
    key = _index_key(text, chunk_size, chunk_overlap, embed_model_name)
    index_dir = INDEX_ROOT / key
    cache_hit = index_dir.exists() and not force_rebuild
    if cache_hit:
        return load_index_run(index_dir, embed_model_name)
    else:
        return build_index_run(text, index_dir, chunk_size, chunk_overlap, embed_model_name)


def format_docs(retrieved_docs):
  context = " ".join(doc.page_content for doc in retrieved_docs)
  return context

 


@tool
def get_relevent_transcript_docs(video_id:str, query:str):
    """
    Retrieve transcript segments from a YouTube video that are relevant to a given query.
    This function fetches the transcript of a specified YouTube video using its video ID,
    analyzes the transcript content, and returns only the text segments that are contextually
    related to the provided query.
    """
    transcript = get_youtube_transcript(video_id)
    vs = load_or_build_index(transcript)
    retriever = vs.as_retriever(search_type='similarity', search_kwargs={'k':4})
    relevent_text= format_docs(retriever.invoke(query))
    return relevent_text
