"""Fleet assistant: answers questions using only the fleet's own numbers.

The AI knows nothing about our robots by itself. Each time someone asks a
question, we collect the current facts from the database, put them in front
of the AI with strict rules, and ask it to answer from those facts only.
This is called grounding.
"""
from nr6.llm import ask
from nr6.metrics import fleet_metrics as m

RULES = """You are the NR6 fleet analyst for a robotics-as-a-service company.
Answer the user's question using ONLY the fleet facts provided.
Rules:
- If the facts do not contain the answer, say so plainly. Never guess or invent numbers.
- Refer to robots by their ID (for example NR6-0009) and vendor.
- Keep answers short and practical: a few sentences or a short list.
- When you recommend an action, give the reason from the facts.
- What the columns mean:
  - interventions: how many times a person had to step in (a new fault started).
  - interventions_per_robot_hour: interventions divided by hours worked. Lower is better.
  - pct_time_in_fault: share of time the robots spent stuck in a fault state. This is NOT a prediction.
  - availability_pct: share of time the robot was not in a fault state.
  - fault_risk_next_6h_pct: the health model's predicted chance of a new fault in the next 6 hours.
    Only this column is a prediction. If it is missing, say risk scores are not available.
  - sla_uptime_pct: the uptime NR6 promised that site (the SLA).
  - uptime_pct: the uptime the site's robots actually delivered.
  - margin_pct: uptime_pct minus sla_uptime_pct. Below zero means the promise was missed.
  - sla_met: True when the promise was kept.
- Each robot works at one site, and each site belongs to one customer.
- Use British English. The data is simulated."""


def fleet_facts(risk=None):
    """Collect the current fleet numbers and turn them into plain text for the AI."""
    summary = m.fleet_summary().iloc[0]
    vendors = m.by_vendor()
    vendors["per_robot_hour"] = (vendors["interventions"] / vendors["robot_hours"]).round(3)
    vendors = vendors.rename(columns={"fault_pct": "pct_time_in_fault",
                                      "per_robot_hour": "interventions_per_robot_hour"})
    robots = m.robot_table().merge(m.inventory_table()[["robot", "model", "site"]], on="robot", how="left")
    sites = m.by_site().drop(columns="robot_hours")

    if risk is not None:
        cols = ["robot", "risk", "temp_avg_last_6h", "faults_last_24h"]
        robots = robots.merge(risk[cols], on="robot", how="left")
        robots["risk"] = (robots["risk"] * 100).round(0)
        robots = robots.rename(columns={"risk": "fault_risk_next_6h_pct",
                                        "temp_avg_last_6h": "motor_temp_6h_avg_c"})

    per_hour = summary["interventions"] / summary["robot_hours"]
    return f"""PERIOD: {summary['period_start'][:16]} to {summary['period_end'][:16]} (UTC)

FLEET TOTALS
robots: {summary['robots']:.0f}
robot_hours_worked: {summary['robot_hours']:.0f}
interventions: {summary['interventions']:.0f}
interventions_per_robot_hour: {per_hour:.3f}
availability_pct: {summary['availability_pct']:.1f}

BY VENDOR
{vendors.round(3).to_csv(index=False)}
BY SITE
{sites.round(2).to_csv(index=False)}
BY ROBOT
{robots.round(2).to_csv(index=False)}"""


def answer(question, risk=None):
    """Answer one question about the fleet, grounded in the current facts."""
    prompt = f"FLEET FACTS\n{fleet_facts(risk)}\nQUESTION\n{question}"
    return ask(RULES, prompt)


if __name__ == "__main__":
    print("These are the facts the AI will see:\n")
    print(fleet_facts())
    question = "Which sites are missing their uptime promise, and which robot is the cause?"
    print(f"\nQuestion: {question}\n")
    print(answer(question))