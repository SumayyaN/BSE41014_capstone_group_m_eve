import streamlit as st
from agent.state import SessionState
from llm_client import ask_llm
from tools.orchestrate import run_tool_turn

st.set_page_config(page_title="MAK Student Support (Baseline)")
st.title("Makerere Freshman Support AI")

# --- Week 5: session state now lives in one SessionState object (Agent Task
# Contract, Section 4) instead of loose st.session_state fields, so the
# orchestrator can enforce the Section 5 limits (max 1 draft per session,
# max 3 tool calls per turn) and log every tool call for evidence/traces.
# "messages" is kept separately - it is the chat *display* list, which is a
# UI concern; conversation_history inside SessionState is the model-context
# copy the orchestrator actually reads.
if "agent_state" not in st.session_state:
    st.session_state.agent_state = SessionState()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for prompt version switching
with st.sidebar:
    st.header("Settings")
    prompt_version = st.selectbox(
        "Prompt Version",
        ["v1.0", "v1.1", "v1.2", "v1.3"],
        help="Switch prompt versions for comparison"
    )
    prompt_file = "v1.3_tools.txt" if prompt_version == "v1.3" else f"{prompt_version}_baseline.txt"
    st.write(f"Using: `{prompt_file}`")
    if prompt_version == "v1.3":
        st.divider()
        st.subheader("Support draft")
        agent_state: SessionState = st.session_state.agent_state
        if agent_state.draft_already_created():
            st.info(f"This session already has a draft: {agent_state.active_case_id}. "
                     "Only one draft is created per session.")
        else:
            st.caption("The case tool stays off until you agree.")
            if st.button("I agree to save a support draft"):
                agent_state.case_agreed = True
            if agent_state.case_agreed:
                st.success("Agreement recorded for this chat.")
            else:
                st.info("No agreement yet. Search still works.")

# Caption reflects the actually selected version, so it never goes stale
# again as new prompt versions are added.
CAPTIONS = {
    "v1.0": "v1.0 — No RAG, No Tools, No Memory",
    "v1.1": "v1.1 — No RAG, No Tools, No Memory",
    "v1.2": "v1.2 — RAG-grounded answers, No Tools, No Memory",
    "v1.3": "v1.3 — Two tools. The app decides which calls run.",
}
st.caption(CAPTIONS.get(prompt_version, ""))

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("trace"):
            st.caption("Tools used: " + ", ".join(step["tool"] for step in msg["trace"]))
        if msg.get("stop_condition"):
            st.caption(f"Stop condition: {msg['stop_condition']}")

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
                trace = []
                stop_condition = None
                if prompt_version == "v1.3":
                    result = run_tool_turn(st.session_state.agent_state, question)
                    answer = result["text"]
                    trace = result["trace"]
                    stop_condition = result.get("stop_condition")
                else:
                    answer = ask_llm(question, prompt_version=prompt_version)
                st.write(answer)
                if trace:
                    st.caption("Tools used: " + ", ".join(step["tool"] for step in trace))
                if stop_condition:
                    st.caption(f"Stop condition: {stop_condition}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "trace": trace,
                    "stop_condition": stop_condition,
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
