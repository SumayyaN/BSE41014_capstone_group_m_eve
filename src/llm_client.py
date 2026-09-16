import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt(version: str = "v1.0") -> str:
    """Load system prompt from file."""
    prompt_path = PROMPTS_DIR / f"{version}_baseline.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()

def ask_llm(question: str, prompt_version: str = "v1.0") -> str:
    """Send a question to Gemini and return the response."""
    system_prompt = load_prompt(prompt_version)

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=question,
        system_instruction=system_prompt,
        generation_config={
            "thinking_level": "low"
        }
    )

    return interaction.output_text