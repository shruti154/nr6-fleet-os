import streamlit as st

from nr6.assistant import answer, fleet_facts
from nr6.health_model import current_risk, train_model
from nr6.llm import setting
from nr6.metrics import fleet_metrics as m
from nr6.ui import apply_style

st.set_page_config(page_title="Fleet assistant · NR6 Fleet OS", layout="wide")
apply_style()

st.html('<div class="eyebrow">Fleet assistant · AI</div>')
st.title("Ask the fleet")
st.caption("Answers come only from this fleet's own numbers and the health model's risk scores.")

# ---------- Is an AI key set up? ----------
provider = setting("AI_PROVIDER", "gemini")
key_name = "ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"
if not setting(key_name):
    st.info(f"No AI key found. Add {key_name} to .streamlit/secrets.toml (or the app's Secrets on Streamlit Cloud).")
    st.stop()


# ---------- The same health model as the dashboard, trained once ----------
@st.cache_resource(show_spinner="Training the health model (first run only)...")
def get_health_model():
    return train_model()


risk = current_risk(m.all_telemetry(), get_health_model())

# ---------- Conversation ----------
if "chat" not in st.session_state:
    st.session_state.chat = []      # list of {"role": "user" or "assistant", "text": ...}

SUGGESTIONS = [
    "Which robot should an engineer check first today, and why?",
    "Which vendor is the least reliable?",
    "Write a two-sentence uptime summary for a customer.",
]


def use_suggestion():
    """When a suggested question is clicked, queue it and clear the selection."""
    st.session_state.pending = st.session_state.suggestion
    st.session_state.suggestion = None


st.pills("Try a question", SUGGESTIONS, key="suggestion", on_change=use_suggestion)
typed = st.chat_input("Ask about the fleet...")
question = typed or st.session_state.pop("pending", None)

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

if question:
    st.session_state.chat.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Reading the fleet data..."):
            try:
                reply = answer(question, risk)
            except Exception as error:
                reply = f"Sorry, the AI service did not answer ({type(error).__name__}). Please try again in a minute."
        st.markdown(reply)
    st.session_state.chat.append({"role": "assistant", "text": reply})

# ---------- Transparency: exactly what the AI was shown ----------
with st.expander("What the AI can see"):
    st.caption("This text is sent with every question. The AI is told to use nothing else.")
    st.code(fleet_facts(risk), language=None)

st.caption(f"AI provider: {provider}. All data is simulated.")