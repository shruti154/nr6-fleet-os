import altair as alt
import streamlit as st

from nr6.metrics import fleet_metrics as m
from nr6.ui import GREEN, INK, RED, STATE_COLOURS, apply_style

st.set_page_config(page_title="Customers · NR6 Fleet OS", layout="wide")
apply_style()

st.html('<div class="eyebrow">Customers · service levels</div>')
st.title("Are we keeping our promises?")
st.caption("Each site has an agreed uptime target (the SLA). This page compares it with what the robots actually delivered.")

# ---------- Data ----------
sites = m.by_site()
robots = m.robot_table().merge(m.inventory_table(), on="robot")
sites["status"] = sites["sla_met"].map({True: "Met", False: "Missed"})

met = int(sites["sla_met"].sum())
worst = sites.sort_values("margin_pct").iloc[0]

# ---------- Headline numbers ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Sites meeting their SLA", f"{met} of {len(sites)}", border=True)
k2.metric("Customers", f"{sites['customer'].nunique()}", border=True)
k3.metric("Robots deployed", f"{sites['robots'].sum():.0f}", border=True)
k4.metric("Smallest margin vs target", f"{worst['margin_pct']:+.2f} pts", worst["site"],
          delta_color="off", delta_arrow="off", border=True,
          help="The site with the smallest gap between actual uptime and its target. Below zero means the promise was missed.")

# ---------- Uptime against target, one row per site ----------
with st.container(border=True, key="panel_sla"):
    st.subheader("Uptime against target")
    colour = alt.Color("status:N", legend=None,
                       scale=alt.Scale(domain=["Met", "Missed"], range=[GREEN, RED]))
    low = min(sites["uptime_pct"].min(), sites["sla_uptime_pct"].min()) - 0.5
    x_scale = alt.Scale(domain=[low, 100])
    base = alt.Chart(sites).encode(y=alt.Y("site:N", title=None, sort=None, axis=alt.Axis(labelLimit=260)))

    gap = base.mark_rule(strokeWidth=3).encode(
        x=alt.X("sla_uptime_pct:Q", scale=x_scale, title="Uptime %"), x2="uptime_pct:Q", color=colour)
    target = base.mark_tick(thickness=3, size=26, color=INK).encode(
        x="sla_uptime_pct:Q",
        tooltip=[alt.Tooltip("site:N"), alt.Tooltip("sla_uptime_pct:Q", title="Target %")])
    actual = base.mark_circle(size=170, opacity=1).encode(
        x="uptime_pct:Q", color=colour,
        tooltip=[alt.Tooltip("site:N"), alt.Tooltip("customer:N"),
                 alt.Tooltip("uptime_pct:Q", format=".2f", title="Actual %"),
                 alt.Tooltip("sla_uptime_pct:Q", title="Target %"),
                 alt.Tooltip("margin_pct:Q", format="+.2f", title="Margin (pts)")])
    # The number sits on the outside of the dot, so it never covers the line
    label_met = base.transform_filter(alt.datum.sla_met).mark_text(
        align="left", dx=12, font="IBM Plex Mono", color=INK).encode(
        x="uptime_pct:Q", text=alt.Text("uptime_pct:Q", format=".2f"))
    label_missed = base.transform_filter(~alt.datum.sla_met).mark_text(
        align="right", dx=-12, font="IBM Plex Mono", color=INK).encode(
        x="uptime_pct:Q", text=alt.Text("uptime_pct:Q", format=".2f"))
    st.altair_chart((gap + target + actual + label_met + label_missed).properties(height=60 * len(sites)), width="stretch")
    st.caption("White bar: the promised uptime. Dot: what was delivered. Green dot: promise kept. Red dot: promise missed.")

# ---------- One section per customer ----------
for customer, customer_sites in sites.groupby("customer", sort=False):
    st.subheader(customer)
    for _, site in customer_sites.iterrows():
        colour_hex = GREEN if site["sla_met"] else RED
        with st.container(border=True, key=f"panel_site_{site['site'].replace(' ', '_')}"):
            left, right = st.columns([1, 2])
            with left:
                st.markdown(f"**{site['site']}**")
                count = int(site["robots"])
                st.caption(f"{site['sector'].title()} · {count} robot{'s' if count != 1 else ''}")
                st.html(f'<span class="chip"><span class="dot" style="background:{colour_hex}"></span>'
                        f'SLA {site["status"].upper()}</span>')
                st.metric("Uptime", f"{site['uptime_pct']:.2f}%",
                          f"{site['margin_pct']:+.2f} pts vs {site['sla_uptime_pct']:.1f}% target")
            with right:
                here = robots[robots["site"] == site["site"]]
                table = here[["robot", "model", "current_state", "interventions", "availability_pct"]].style.map(
                    lambda s: f"color: {STATE_COLOURS.get(s, INK)}; font-weight: 600", subset=["current_state"])
                st.dataframe(table, hide_index=True, width="stretch", column_config={
                    "robot": "Robot", "model": "Model", "current_state": "State now",
                    "interventions": st.column_config.NumberColumn("Interventions", format="%d"),
                    "availability_pct": st.column_config.NumberColumn("Availability", format="%.2f%%"),
                })

st.caption("All data is simulated. Customer names are made up for the demo.")