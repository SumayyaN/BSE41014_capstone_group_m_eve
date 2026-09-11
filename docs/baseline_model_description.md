Overview
The baseline is a freshman-scoped chat application. A student asks a question, the app sends it to Gemini 3.6 Flash via the Google Interactions API, and the response is displayed. Answers come from the model's general training data only — no documents, no tools, no memory, no agent loop.

Code Structure
File	Role
src/app.py	Streamlit chat UI. Captures input, keeps session history, lets the user pick a prompt version.
src/llm_client.py	Loads the prompt file, calls Gemini, returns the response text.
src/prompts/v1.0_baseline.txt	Initial freshman-scoped system prompt.
src/prompts/v1.1_baseline.txt	Improved prompt with stricter scope and fallback rules.
.env	Stores GEMINI_API_KEY (never committed).
requirements.txt	google-genai, streamlit, python-dotenv.
.gitignore	Excludes .env, .venv/, and cache folders.
How the Model Operates
text
Student → Streamlit app → llm_client → Gemini API → response → Streamlit app → Student
Student types a question into st.chat_input.

App reads the selected prompt version from the sidebar.

load_prompt() reads the matching prompt file.

ask_llm() calls client.interactions.create() with model gemini-3.6-flash, the question, the system instruction, and thinking_level="low".

Gemini returns an interaction object; the function returns interaction.output_text.

The answer is rendered in the chat and stored in st.session_state.messages.

Scope and Behaviour Control
The system prompt is the only behaviour control. It defines the role (freshman support assistant), the scope (onboarding only: webmail, MUELE, Wi-Fi, registration, fee onboarding, password resets), the safety rules (no admissions, grading, disciplinary, or fee decisions; no invented specifics), and the fallback (admit uncertainty, refuse out-of-scope questions).

Session State
st.session_state.messages stores chat history for the current session only. It clears on reload. The model does not receive prior messages as context in Week 2.

Known Limitations
No document grounding, no citations, hallucinated specifics, no tools, no agent loop, no persistent memory, no evaluation dataset, and no way to verify a user is truly a freshman. These are addressed in Weeks 3 through 7.

Reproduction
Clone the repo.

python -m venv .venv and activate it.

pip install -r requirements.txt.

Create .env with GEMINI_API_KEY=<key>.

From src/: streamlit run app.py.

Open http://localhost:8501.

