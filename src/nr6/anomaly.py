"""Anomaly detection: is a robot behaving unlike its own normal self?

The health model can only spot problems it has learned from past faults
(worn, hot motors). This needs no fault history at all. For each robot it
learns what "normal" looks like from that robot's own recent past, then
measures how far the last few hours have drifted from it, on each signal.
So it can catch problems nobody has seen before, such as a failing battery.
"""
import random

import pandas as pd

from nr6.pipeline import run_pipeline
from nr6.sim.vendor_messages import SIM_START

RECENT_HOURS = 6        # "now" = the average of the last 6 hours
BASELINE_HOURS = 72     # "normal" = the 3 days before that
MIN_BASELINE = 24       # need at least a day of history before judging
THRESHOLD = 4.0         # drift score above this counts as unusual

# The signals we watch, and the smallest "usual variation" we allow for each
SIGNALS = {
    "motor_temp": ("motor temperature", "°C", 1.0),
    "battery_drain": ("battery use per working hour", "% per hour", 0.5),
}


def hourly_signals(g):
    """One robot's telemetry -> one row per hour with each signal's average."""
    g = g.sort_values("observed_at")
    working = g["state"] == "WORKING"
    both_working = working & working.shift(1, fill_value=False)
    # Battery drop between two reports in a row while working, scaled to a full hour
    drop = -g["battery_pct"].diff() * 12

    return pd.DataFrame({
        "motor_temp": g["motor_temp_c"].where(working).groupby(g["hour"]).mean(),
        "battery_drain": drop.where(both_working).groupby(g["hour"]).mean(),
    })


def drift(series, floor):
    """How far the last 6 hours are from this robot's own normal, in 'usual variations'.
    0 = exactly normal. 4 = four times further than it usually moves."""
    recent = series.rolling(RECENT_HOURS, min_periods=3).mean()
    past = series.shift(RECENT_HOURS)                       # baseline stops where 'recent' starts
    normal = past.rolling(BASELINE_HOURS, min_periods=MIN_BASELINE).median()
    variation = (1.4826 * (past - normal).abs()
                 .rolling(BASELINE_HOURS, min_periods=MIN_BASELINE).median()).clip(lower=floor)
    return (recent - normal) / variation, recent, normal


def drift_scores(telemetry):
    """One row per robot per hour: the drift on each signal, and the worst one."""
    df = telemetry.copy()
    df["hour"] = pd.to_datetime(df["observed_at"]).dt.floor("h")

    rows = []
    for robot, g in df.groupby("robot_serial"):
        h = hourly_signals(g)
        for name, (_, _, floor) in SIGNALS.items():
            h[f"{name}_drift"], h[f"{name}_recent"], h[f"{name}_normal"] = drift(h[name], floor)
        drift_cols = [f"{name}_drift" for name in SIGNALS]
        h = h.dropna(subset=drift_cols, how="all")              # not enough history yet
        h["score"] = h[drift_cols].abs().max(axis=1)
        h["signal"] = h[drift_cols].abs().fillna(-1).idxmax(axis=1).str.replace("_drift", "")
        h["robot"] = robot
        h["vendor"] = g["vendor"].iloc[0]
        rows.append(h.reset_index())

    scores = pd.concat(rows, ignore_index=True)
    scores["unusual"] = scores["score"] > THRESHOLD
    return scores


def explain(row):
    """Turn the worst signal into a sentence a person can act on."""
    label, unit, _ = SIGNALS[row["signal"]]
    recent, normal = row[f"{row['signal']}_recent"], row[f"{row['signal']}_normal"]
    direction = "higher" if recent > normal else "lower"
    return f"{label} {direction} than its normal: {recent:.1f} vs {normal:.1f} {unit}"


def current_anomalies(telemetry):
    """One row per robot: how unusual it is right now, and why."""
    scores = drift_scores(telemetry)
    rows = []
    for robot, g in scores.groupby("robot"):
        last = g.iloc[-1]
        rows.append({
            "robot": robot,
            "vendor": last["vendor"],
            "score": last["score"],
            "unusual": bool(last["unusual"]),
            "unusual_hours_last_24h": int(g.tail(24)["unusual"].sum()),
            "why": explain(last),
        })
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    # Plant a hidden battery fault, then see whether the detector finds it on its own
    planted = {"robot": "NR6-0004", "from_day": 6, "drain_times": 1.8}
    random.seed(42)
    order = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}
    scores = drift_scores(run_pipeline(order, days=7, battery_fault=planted))

    start = pd.Timestamp(SIM_START) + pd.Timedelta(days=planted["from_day"])
    faulty = scores[scores["robot"] == planted["robot"]]
    caught = faulty[(faulty["hour"] >= start) & faulty["unusual"]]
    others = scores[scores["robot"] != planted["robot"]]

    print(f"Planted: {planted['robot']}'s battery drains {planted['drain_times']}x faster from {start:%a %d %b %H:%M}")
    if caught.empty:
        print("Missed: the detector never flagged it.")
    else:
        first = caught.iloc[0]
        delay = (first["hour"] - start).total_seconds() / 3600
        print(f"Caught: first flagged at {first['hour']:%a %H:%M}, {delay:.0f} hour{'s' if round(delay) != 1 else ''} after it started")
        print(f"        reason: {explain(first)}")
    print(f"False alarms on the other robots: {others['unusual'].sum()} of {len(others):,} robot-hours "
          f"({others['unusual'].mean():.1%})")