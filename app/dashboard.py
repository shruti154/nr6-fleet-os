import random

import altair as alt
import pandas as pd
import streamlit as st

from nr6.catalogue import load_catalogue
from nr6.metrics import fleet_metrics as m
from nr6.pipeline import ADAPTERS, run_pipeline, save_telemetry

st.set_page_config(page_title="NR6 Fleet OS", layout="wide")

# ---------- Design tokens: every colour used on the page, in one place ----------
INK = "#E4EAF0"        # main text
MUTED = "#93A3B5"      # labels, axes
SURFACE = "#141E28"    # card background
LINE = "#263443"       # borders
BLUE = "#7CC4F5"       # main accent
YELLOW = "#F5C542"     # "watch this"
VENDOR_COLOURS = {"Keenon": "#8A9BB0", "Pudu": BLUE, "Unitree": YELLOW}
STATE_COLOURS = {"WORKING": "#5CC08A", "CHARGING": BLUE, "FAULT": "#F2685C",
                 "IDLE": MUTED, "OFFLINE": MUTED}

# ---------- Page styling (CSS) ----------
st.html(f"""
<style>
  .block-container {{ padding-top: 2.2rem; }}
  .eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; letter-spacing: 0.14em;
              text-transform: uppercase; color: {BLUE}; margin-bottom: 0.2rem; }}
  .status-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end; padding-top: 1.6rem; }}
  .chip {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; padding: 0.3rem 0.7rem;
           border: 1px solid {LINE}; border-radius: 999px; color: {INK}; background: {SURFACE}; }}
  .chip b {{ font-weight: 500; margin-left: 0.35rem; }}
  .dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 0.4rem; }}
  .st-key-panel, .st-key-panel2 {{ background: {SURFACE}; }}
  .board {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 0.6rem; }}
  .tile {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 4px; padding: 0.7rem 0.8rem; }}
  .tile .id {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: {INK}; }}
  .tile .vendor {{ font-size: 0.75rem; color: {MUTED}; margin-bottom: 0.5rem; }}
  .tile .state {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.06em; }}
  .tile .bar {{ height: 4px; background: {LINE}; border-radius: 2px; margin-top: 0.55rem; overflow: hidden; }}
  .tile .bar i {{ display: block; height: 100%; }}
  .stButton button[kind="primary"] {{ color: #0E151D; font-weight: 600; }}
</style>
""")


# Charts follow the same quiet style as the page
@alt.theme.register("nr6", enable=True)
def nr6_chart_theme():
    return {"config": {
        "font": "Public Sans",
        "background": "transparent",
        "axis": {"labelColor": MUTED, "titleColor": MUTED, "gridColor": "#1F2B38",
                 "domainColor": "#33445A", "tickColor": "#33445A", "titleFontWeight": 500},
        "legend": {"labelColor": INK},
        "view": {"stroke": None},
    }}


# ---------- Sidebar: build a fleet and run a new simulation ----------
DEFAULT_FLEET = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}

with st.sidebar:
    st.html('<div class="eyebrow">Simulation controls</div>')
    st.subheader("Build a fleet")

    catalogue, _ = load_catalogue()
    has_adapter = catalogue["vendor"].isin(list(ADAPTERS))
    order = {}
    for _, robot in catalogue[has_adapter].iterrows():
        order[robot["id"]] = st.number_input(
            robot["name"], min_value=0, max_value=20, step=1,
            value=DEFAULT_FLEET.get(robot["id"], 0), key=f"qty_{robot['id']}",
            help=f"{robot['category']} · £{robot['price_gbp']:,.0f} each",
        )

    waiting = sorted(catalogue[~has_adapter]["vendor"].unique())
    if waiting:
        st.caption(f"Not available yet: {', '.join(waiting)} (no adapter written)")

    days = st.slider("Days to simulate", min_value=1, max_value=14, value=7)
    seed = st.number_input("Random seed", min_value=0, max_value=9999, value=42,
                           help="Same seed and fleet give the same result every time.")

    if st.button("Run simulation", type="primary", width="stretch"):
        chosen = {robot_id: qty for robot_id, qty in order.items() if qty > 0}
        if not chosen:
            st.warning("Add at least one robot first.")
        else:
            with st.spinner("Simulating the fleet..."):
                random.seed(seed)
                save_telemetry(run_pipeline(chosen, days))
            st.toast(f"Simulated {sum(chosen.values())} robots for {days} days")

# ---------- Data ----------
summary = m.fleet_summary().iloc[0]
vendors = m.by_vendor()
vendors["per_robot_hour"] = vendors["interventions"] / vendors["robot_hours"]
daily = m.interventions_by_day()
kpis = m.daily_kpis()
kpis["per_robot_hour"] = kpis["interventions"] / kpis["robot_hours"]
robots = m.robot_table()
robots["interventions"] = robots["interventions"].astype(int)

start = pd.Timestamp(summary["period_start"]).strftime("%a %d %b")
end = pd.Timestamp(summary["period_end"]).strftime("%a %d %b %Y")
per_robot_hour = summary["interventions"] / summary["robot_hours"]
state_counts = robots["current_state"].value_counts()

# Only show vendors that are actually in this fleet, each in its own colour
present = [v for v in VENDOR_COLOURS if v in set(vendors["vendor"])]
vendor_scale = alt.Scale(domain=present, range=[VENDOR_COLOURS[v] for v in present])

# ---------- Header ----------
head_left, head_right = st.columns([1.3, 1])
with head_left:
    st.html('<div class="eyebrow">Fleet command · simulated</div>')
    st.title("NR6 Fleet OS")
    st.caption(f"Mixed-vendor fleet  ·  {start} to {end}  ·  telemetry every 5 minutes")
with head_right:
    chips = "".join(
        f'<span class="chip"><span class="dot" style="background:{STATE_COLOURS[s]}"></span>'
        f'{s.title()}<b>{state_counts.get(s, 0)}</b></span>'
        for s in ["WORKING", "CHARGING", "FAULT", "IDLE"]
    )
    st.html(f'<div class="status-row">{chips}</div>')

# ---------- Headline numbers, each with a 7-day trend line ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Interventions per robot-hour", f"{per_robot_hour:.3f}", border=True,
          chart_data=kpis["per_robot_hour"].round(3), chart_type="area",
          help="North-star metric: how often a person has to help a robot, per hour of work. Lower is better.")
c2.metric("Availability", f"{summary['availability_pct']:.1f}%", border=True,
          chart_data=kpis["availability_pct"].round(2), chart_type="area",
          help="Share of time robots were not in a fault state.")
c3.metric("Interventions", f"{summary['interventions']:,.0f}", border=True,
          chart_data=kpis["interventions"], chart_type="bar")
c4.metric("Robot-hours worked", f"{summary['robot_hours']:,.0f}", border=True,
          chart_data=kpis["robot_hours"].round(1), chart_type="bar",
          help=f"{summary['robots']:.0f} robots")

# ---------- Fleet board: every robot at a glance ----------
st.subheader("Fleet now")
tiles = ""
for _, r in robots.sort_values("robot").iterrows():
    colour = STATE_COLOURS.get(r["current_state"], MUTED)
    tiles += (
        f'<div class="tile"><div class="id">{r["robot"]}</div>'
        f'<div class="vendor">{r["vendor"]}</div>'
        f'<div class="state" style="color:{colour}"><span class="dot" style="background:{colour}"></span>'
        f'{r["current_state"]}</div>'
        f'<div class="bar"><i style="width:{r["battery"]:.0f}%;background:{colour}"></i></div></div>'
    )
st.html(f'<div class="board">{tiles}</div>')

st.write("")

# ---------- Charts ----------
left, right = st.columns([1, 1.4])

vendor_order = vendors.sort_values("per_robot_hour", ascending=False)["vendor"].tolist()

with left.container(border=True, key="panel"):
    st.subheader("Interventions per robot-hour")
    bar = (
        alt.Chart(vendors)
        .mark_bar(size=30, cornerRadiusEnd=2)
        .encode(
            y=alt.Y("vendor:N", title=None, sort=vendor_order),
            x=alt.X("per_robot_hour:Q", title=None),
            color=alt.Color("vendor:N", legend=None, scale=vendor_scale),
            tooltip=[alt.Tooltip("vendor:N"), alt.Tooltip("robots:Q"), alt.Tooltip("interventions:Q"),
                     alt.Tooltip("per_robot_hour:Q", format=".3f", title="per robot-hour")],
        )
        .properties(height=230)
    )
    labels = bar.mark_text(align="left", dx=6, font="IBM Plex Mono").encode(
        text=alt.Text("per_robot_hour:Q", format=".3f"), color=alt.value(INK))
    st.altair_chart(bar + labels, width="stretch")

with right.container(border=True, key="panel2"):
    st.subheader("New faults per day")
    base = alt.Chart(daily).encode(
        x=alt.X("day:T", title=None, axis=alt.Axis(format="%a %d", grid=False)),
        y=alt.Y("interventions:Q", title=None),
        tooltip=[alt.Tooltip("day:T", format="%A %d %b"), "vendor:N", "interventions:Q"],
    )
    # Soft fill under the humanoid's line: the series to watch
    area = (base.transform_filter(alt.datum.vendor == "Unitree")
            .mark_area(opacity=0.10, interpolate="monotone", color=YELLOW))
    lines = base.mark_line(strokeWidth=2, interpolate="monotone").encode(
        color=alt.Color("vendor:N", title=None, scale=vendor_scale,
                        legend=alt.Legend(orient="top", direction="horizontal")))
    points = base.mark_circle(size=34).encode(
        color=alt.Color("vendor:N", scale=vendor_scale, legend=None))
    st.altair_chart((area + lines + points).properties(height=230), width="stretch")

# ---------- Robot table ----------
st.subheader("Robots")
table = robots.style.map(
    lambda s: f"color: {STATE_COLOURS.get(s, INK)}; font-weight: 600", subset=["current_state"]
)
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "robot": st.column_config.TextColumn("Robot"),
        "vendor": st.column_config.TextColumn("Vendor"),
        "current_state": st.column_config.TextColumn("State now"),
        "battery": st.column_config.ProgressColumn("Battery", format="%d%%", min_value=0, max_value=100),
        "hours_worked": st.column_config.NumberColumn("Hours worked", format="%.1f"),
        "interventions": st.column_config.NumberColumn("Interventions"),
        "availability_pct": st.column_config.NumberColumn("Availability", format="%.1f%%"),
    },
)

st.caption("All data is simulated. Fault rates are assumptions for illustration, not vendor measurements.")