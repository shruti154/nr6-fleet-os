from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_FILE = PROJECT_ROOT / "data" / "fleet.duckdb"
SIM_START = pd.Timestamp("2026-10-19 07:00")   # the simulated Monday morning


def save_run(events, fleet, path=DB_FILE):
    """Save one simulation run into the database as two tables: events and robots."""

    # Table 1: every event, with a real date and time instead of a tick number
    events_df = pd.DataFrame(events, columns=["tick", "robot_id", "model", "event"])
    events_df["event_time"] = SIM_START + pd.to_timedelta(events_df["tick"] * 5, unit="min")

    # Table 2: one row per robot with its totals
    rows = []
    for robot in fleet:
        rows.append({
            "robot_id": robot.robot_id,
            "model": robot.model,
            "hours_worked": round(robot.hours_worked, 2),
            "interventions": robot.interventions,
        })
    robots_df = pd.DataFrame(rows)

    # Write both tables into the database file
    con = duckdb.connect(str(path))
    con.register("events_df", events_df)
    con.register("robots_df", robots_df)
    con.execute("CREATE OR REPLACE TABLE events AS SELECT * FROM events_df")
    con.execute("CREATE OR REPLACE TABLE robots AS SELECT * FROM robots_df")
    con.close()
    print(f"Saved {len(events_df)} events and {len(robots_df)} robots to {path.name}")