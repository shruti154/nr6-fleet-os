"""One door to any AI model.

The rest of the app only ever calls ask(). Which AI answers is decided by the
AI_PROVIDER setting, the same way each robot brand has its own adapter.
"""
import os
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def setting(name, default=None):
    """Read a setting: first from the environment (how Streamlit Cloud provides
    secrets), then from .streamlit/secrets.toml on your laptop."""
    if name in os.environ:
        return os.environ[name]
    if SECRETS_FILE.exists():
        with open(SECRETS_FILE, "rb") as f:
            return tomllib.load(f).get(name, default)
    return default


def ask_gemini(system, prompt):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=setting("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=setting("GEMINI_MODEL", "gemini-flash-latest"),
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.2),
    )
    return response.text


def ask_claude(system, prompt):
    import anthropic

    client = anthropic.Anthropic(api_key=setting("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=setting("CLAUDE_MODEL", "claude-haiku-5-5"),
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# One entry per AI provider: name -> function that asks it a question
PROVIDERS = {
    "gemini": ask_gemini,
    "claude": ask_claude,
}


def ask(system, prompt):
    """Send instructions (system) and a question (prompt) to the chosen AI."""
    provider = setting("AI_PROVIDER", "gemini")
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown AI_PROVIDER '{provider}'. Use one of: {', '.join(PROVIDERS)}")
    return PROVIDERS[provider](system, prompt)


if __name__ == "__main__":
    print(f"Provider: {setting('AI_PROVIDER', 'gemini')}")
    print(f"Key found: {'yes' if setting('GEMINI_API_KEY') or setting('ANTHROPIC_API_KEY') else 'NO'}")
    reply = ask("You are a friendly assistant. Answer in one short sentence.",
                "Say hello to Shruti and confirm the NR6 Fleet OS connection works.")
    print(f"\nAI says: {reply}")