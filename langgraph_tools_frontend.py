import streamlit as st
from langgraph_tools_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid


#utility functions
def generate_thread_id():
    thread_id = str(uuid.uuid4())
    st.session_state['chat_threads'].append(thread_id)
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []

def load_conversation(thread_id : str):
    config = {'configurable': {'thread_id': thread_id}}
    values = chatbot.get_state(config=config).values
    if values:
        return values['messages']
    return []


#this whole code runs from top to bottom everytime input is recieved.
#that's why we use a particular dictionary that persists.

#st.session_state is a dictionary in itself. we add a key named message_history to it which is a list

#session startup
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()




CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}


#sidebar UI

st.sidebar.title('LangGraph ChatBot')
if st.sidebar.button('New Chat'):
    reset_chat()
st.sidebar.header('My Conversations')

for thread_id in reversed(st.session_state['chat_threads']):
    messages = load_conversation(thread_id)

    chat_title = thread_id[:8]
    for m in messages:
        if isinstance(m, HumanMessage):
            chat_title = m.content[:30] + "..." if len(m.content) > 30 else m.content
            break

    if st.sidebar.button(chat_title, key=thread_id):
        st.session_state['thread_id'] = thread_id

        # Build message_history from already-loaded messages
        message_history = []
        for message in messages:
            if isinstance(message, HumanMessage):
                message_history.append({'role': 'user', 'content': message.content})
            else:
                message_history.append({'role': 'assistant', 'content': message.content})

        st.session_state['message_history'] = message_history

            


        


for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here.')

if user_input:

    st.session_state['message_history'].append({'role':'user', 'content':user_input})
    with st.chat_message('user'):
        st.text(user_input)

    response = chatbot.stream({'messages':[HumanMessage(content=user_input)]}, config=CONFIG, stream_mode='messages')



    with st.chat_message("assistant"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                #create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    
        st.session_state['message_history'].append({'role':'assistant', 'content':ai_message})
