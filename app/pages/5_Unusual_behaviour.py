import altair as alt
import streamlit as st

from nr6.anomaly import SIGNALS, THRESHOLD, current_anomalies, drift_scores
from nr6.health_model import current_risk, train_model
from nr6.metrics import fleet_metrics as m
from nr6.ui import BLUE, MUTED, RED, apply_style

st.set_page_config(page_title="Unusual behaviour · NR6 Fleet OS", layout="wide")
apply_style()

st.html('<div class="eyebrow">Anomaly detection · AI</div>')
st.title("Is anything behaving oddly?")
st.caption("Each robot is compared with its own normal over the previous 3 days. "
           "No fault history is needed, so this can catch problems the health model has never seen.")


@st.cache_resource(show_spinner="Training the health model (first run only)...")
def get_health_model():
    return train_model()


telemetry = m.all_telemetry()
now = current_anomalies(telemetry)
scores = drift_scores(telemetry)
risk = current_risk(telemetry, get_health_model()).set_index("robot")["risk"]
now["health_risk"] = now["robot"].map(risk)

now["why"] = now["why"].where(now["unusual"], "within its normal range")
flagged = now[now["unusual"]]

# ---------- Headline numbers ----------
k1, k2, k3 = st.columns(3)
k1.metric("Robots behaving unusually now", f"{len(flagged)} of {len(now)}", border=True)
k2.metric("Signals watched", f"{len(SIGNALS)}", border=True,
          help=", ".join(label for label, _, _ in SIGNALS.values()))
k3.metric("Alarm level", f"drift > {THRESHOLD:.0f}", border=True,
          help="Drift is how far the last 6 hours are from the robot's own normal, "
               "measured in 'usual variations'. 0 means exactly normal.")

# ---------- Every robot, most unusual first ----------
st.subheader("Every robot, most unusual first")
table = now[["robot", "vendor", "score", "why", "health_risk", "unusual_hours_last_24h"]]
st.dataframe(table, hide_index=True, width="stretch", column_config={
    "robot": "Robot", "vendor": "Vendor",
    "score": st.column_config.ProgressColumn("Drift now", format="%.1f", min_value=0.0,
                                             max_value=max(THRESHOLD * 2, float(now["score"].max()))),
    "why": "What changed",
    "health_risk": st.column_config.ProgressColumn("Health model risk, 6h", format="percent",
                                                   min_value=0.0, max_value=1.0),
    "unusual_hours_last_24h": st.column_config.NumberColumn("Unusual hours (24h)"),
})

# ---------- The story of the most unusual robot ----------
top = now.iloc[0]
signal = scores[scores["robot"] == top["robot"]].iloc[-1]["signal"]
label, unit, _ = SIGNALS[signal]
history = scores[scores["robot"] == top["robot"]]

with st.container(border=True, key="panel_anomaly"):
    st.markdown(f"**{top['robot']} ({top['vendor']}) · {label}**")
    base = alt.Chart(history).encode(x=alt.X("hour:T", title=None, axis=alt.Axis(format="%a %H:%M", grid=False)))
    normal = base.mark_line(strokeDash=[4, 4], color=MUTED).encode(
        y=alt.Y(f"{signal}_normal:Q", title=unit))
    recent = base.mark_line(strokeWidth=2, color=BLUE).encode(
        y=f"{signal}_recent:Q",
        tooltip=[alt.Tooltip("hour:T", format="%a %d %b %H:%M"),
                 alt.Tooltip(f"{signal}_recent:Q", format=".1f", title="last 6 hours"),
                 alt.Tooltip(f"{signal}_normal:Q", format=".1f", title="its normal"),
                 alt.Tooltip("score:Q", format=".1f", title="drift")])
    alarms = base.transform_filter(alt.datum.unusual).mark_circle(size=40, color=RED).encode(
        y=f"{signal}_recent:Q")
    st.altair_chart((normal + recent + alarms).properties(height=220), width="stretch")
    st.caption("Blue: the last 6 hours. Dashed grey: this robot's own normal. Red dots: hours flagged as unusual.")

if top["unusual"] and top["health_risk"] < 0.4:
    st.info(f"The health model rates {top['robot']} at only {top['health_risk']:.0%} risk, because it learned "
            f"from motor wear and past faults, not from {label}. The anomaly detector needed no training "
            "to notice the change. The two methods catch different problems, which is why we run both.")

st.caption("All data is simulated. In the starter week, a battery fault is planted in one robot on day 6 "
           "and nothing else in the system is told about it.")