import streamlit as st
from llm_client import ask_llm

st.set_page_config(page_title="MAK Student Support (Baseline)")
st.title("Makerere Freshman Support AI")
st.caption("Week 2 Baseline — No RAG, No Tools, No Memory")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for prompt version switching
with st.sidebar:
    st.header("Settings")
    prompt_version = st.selectbox(
        "Prompt Version",
        ["v1.0"],
        help="Switch prompt versions for comparison"
    )
    st.write(f"Using: `{prompt_version}_baseline.txt`")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle new input
if question := st.chat_input("Ask about university policies..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    
    # Get LLM response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = ask_llm(question, prompt_version=prompt_version)
                st.write(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )