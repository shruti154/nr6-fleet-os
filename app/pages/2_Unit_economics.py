import altair as alt
import pandas as pd
import streamlit as st

from nr6.catalogue import load_catalogue
from nr6.economics import Assumptions, catalogue_economics
from nr6.ui import GREEN, INK, MUTED, RED, YELLOW, apply_style

st.set_page_config(page_title="Unit economics · NR6 Fleet OS", layout="wide")
apply_style()

st.html('<div class="eyebrow">Unit economics · simulated assumptions</div>')
st.title("Does each robot make money?")
st.caption("Monthly money per robot on a subscription contract. Change the assumptions and every number updates.")

# ---------- Assumptions ----------
with st.container(border=True, key="panel_assumptions"):
    st.markdown("**Assumptions**")
    a1, a2, a3, a4, a5 = st.columns(5)
    fee_pct = a1.slider("Monthly fee, % of robot price", 2.0, 8.0, 4.5, 0.1,
                        help="US integrator RobotLAB lists RaaS at roughly 4 to 4.5% of purchase price a month.")
    autonomy = a2.slider("Intervention rate ×", 0.25, 3.0, 1.0, 0.05,
                         help="1 = catalogue fault rate. 0.5 = robots need a person half as often.")
    remote_share = a3.slider("Fixed remotely, %", 0, 100, 70, 5)
    onsite_cost = a4.slider("Engineer visit, £", 40, 250, 110, 5)
    wage = a5.slider("Customer's labour cost, £/hour", 11.0, 30.0, 15.0, 0.5)

assumptions = Assumptions(fee_pct_of_price=fee_pct / 100, autonomy_multiplier=autonomy,
                          remote_fix_share=remote_share / 100, onsite_visit_cost=onsite_cost,
                          loaded_wage_per_hour=wage)

catalogue, _ = load_catalogue()
econ = catalogue_economics(catalogue, assumptions)

# ---------- Per-model table, with an editable quantity column for the fleet ----------
st.subheader("Per robot, per month")
default_qty = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}
econ.insert(0, "qty", econ["id"].map(default_qty).fillna(0).astype(int))
econ["payback"] = econ["payback_months"].map(lambda m: "never" if m == float("inf") else f"{m:.0f} months")

edited = st.data_editor(
    econ.drop(columns=["id", "depreciation", "running_cost", "payback_months"]),
    hide_index=True, width="stretch", key="econ_table",
    disabled=[c for c in econ.columns if c != "qty"],
    column_config={
        "qty": st.column_config.NumberColumn("In fleet", min_value=0, max_value=50, step=1,
                                             help="Edit to build a fleet; totals below update."),
        "name": "Robot", "category": "Category",
        "price_gbp": st.column_config.NumberColumn("Price", format="£%,.0f"),
        "price_status": "Price is",
        "fee": st.column_config.NumberColumn("Fee", format="£%,.0f"),
        "interventions": st.column_config.NumberColumn("Interventions", format="%.1f"),
        "intervention_cost": st.column_config.NumberColumn("Intervention cost", format="£%,.0f"),
        "margin": st.column_config.NumberColumn("Margin", format="£%,.0f"),
        "payback": st.column_config.TextColumn("Payback"),
        "customer_saving": st.column_config.NumberColumn("Customer saves", format="£%,.0f"),
    },
)
st.caption("Placeholder prices are estimates until a supplier quotes. Payback says never when the robot would not earn back its price at these settings.")

# ---------- Fleet totals ----------
fleet = econ.assign(qty=edited["qty"].values)
fleet = fleet[fleet["qty"] > 0]
revenue = (fleet["fee"] * fleet["qty"]).sum()
cost = ((fleet["running_cost"] + fleet["depreciation"]) * fleet["qty"]).sum()
capex = (fleet["price_gbp"] * fleet["qty"]).sum()
margin = revenue - cost

k1, k2, k3, k4 = st.columns(4)
k1.metric("Fleet revenue / month", f"£{revenue:,.0f}", border=True, help=f"{fleet['qty'].sum()} robots")
k2.metric("Fleet cost / month", f"£{cost:,.0f}", border=True, help="Running costs plus depreciation")
k3.metric("Fleet margin / month", f"{'-' if margin < 0 else ''}£{abs(margin):,.0f}", f"{(margin / revenue * 100) if revenue else 0:.0f}% of revenue",
          border=True)
k4.metric("Capital to buy the fleet", f"£{capex:,.0f}", border=True, help="Cash needed before the first invoice")

# ---------- Charts ----------
left, right = st.columns([1, 1.2])

with left.container(border=True, key="panel_margin"):
    st.subheader("Margin per robot, per month")
    margin_chart = (
        alt.Chart(econ)
        .mark_bar(size=18, cornerRadiusEnd=2)
        .encode(
            y=alt.Y("name:N", title=None, sort="-x"),
            x=alt.X("margin:Q", title=None, axis=alt.Axis(labelExpr='"£" + format(datum.value, ",.0f")')),
            color=alt.condition(alt.datum.margin >= 0, alt.value(GREEN), alt.value(RED)),
            tooltip=["name:N", alt.Tooltip("margin:Q", format=",.0f", title="margin £"),
                     alt.Tooltip("intervention_cost:Q", format=",.0f", title="intervention cost")],
        )
        .properties(height=280)
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=MUTED).encode(x="x:Q")
    st.altair_chart(zero + margin_chart, width="stretch")

with right.container(border=True, key="panel_sensitivity"):
    st.subheader("What autonomy is worth to this fleet")
    rows = []
    for mult in [m / 20 for m in range(5, 61)]:          # 0.25 to 3.0 in steps of 0.05
        e = catalogue_economics(catalogue, Assumptions(**{**assumptions.__dict__, "autonomy_multiplier": mult}))
        e = e.merge(fleet[["id", "qty"]], on="id")
        rows.append({"multiplier": mult, "margin": (e["margin"] * e["qty"]).sum()})
    curve = pd.DataFrame(rows)
    line = alt.Chart(curve).mark_line(color=YELLOW, strokeWidth=2).encode(
        x=alt.X("multiplier:Q", title="Intervention rate × (left = more reliable robots)"),
        y=alt.Y("margin:Q", title="Fleet margin / month", axis=alt.Axis(labelExpr='"£" + format(datum.value, ",.0f")')),
        tooltip=[alt.Tooltip("multiplier:Q", format=".2f"), alt.Tooltip("margin:Q", format=",.0f")],
    )
    now = alt.Chart(pd.DataFrame({"x": [autonomy]})).mark_rule(color=INK, strokeDash=[4, 4]).encode(x="x:Q")
    breakeven = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=MUTED).encode(y="y:Q")
    st.altair_chart((breakeven + line + now).properties(height=280), width="stretch")
    st.caption("Dashed line: your current setting. Where the yellow line crosses £0 is break-even.")

st.caption("All figures are illustrative. Fault rates are simulation assumptions, not vendor measurements.")