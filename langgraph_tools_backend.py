from langgraph.graph import START, END, StateGraph
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
import sqlite3
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.documents import Document
from youtube import get_relevent_transcript_docs
from calculator import calculator
from get_stock_price import get_stock_price



load_dotenv()




search_tool = DuckDuckGoSearchRun(region='us-en')
youtube_transcript_tool= get_relevent_transcript_docs
calculator_tool = calculator
stock_price_tool = get_stock_price



    


tools =[search_tool, calculator_tool, stock_price_tool, youtube_transcript_tool]
llm = ChatOpenAI(model='gpt-4.1-nano-2025-04-14')

llm_with_tools = llm.bind_tools(tools=tools)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    messages = [
        {"role": "system", "content": "You can use tools like get_relevent_transcript_docs to fetch YouTube transcripts when users ask follow-up questions about videos."}
    ] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools)

conn = sqlite3.connect('chatbot.db', check_same_thread=False)

checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')
chatbot = graph.compile(checkpointer=checkpointer)


#return all the unique threads 
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)


