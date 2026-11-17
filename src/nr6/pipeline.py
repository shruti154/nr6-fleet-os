import random
from dataclasses import asdict
from datetime import timedelta

import duckdb
import pandas as pd

from nr6.adapters import keenon, pudu, unitree
from nr6.db import DB_FILE
from nr6.sim.fleet import build_fleet
from nr6.sim.robot import TICKS_PER_HOUR
from nr6.sim.vendor_messages import ENCODERS, SIM_START

# One adapter per brand: the vendor's format in, NR6's canonical record out
ADAPTERS = {
    "Pudu": pudu.to_canonical,
    "Keenon": keenon.to_canonical,
    "Unitree": unitree.to_canonical,
}


def run_pipeline(order, days, battery_fault=None):
    """Simulate the fleet. Every 5 minutes, each robot sends a message in its own
    brand's format, and the matching adapter translates it into a canonical record.

    battery_fault (optional) plants a hidden problem for the anomaly detector to find,
    e.g. {"robot": "NR6-0004", "from_day": 6, "drain_times": 1.8}: from day 6, that
    robot's battery drains 1.8 times faster. Nothing else in the system is told."""
    fleet = build_fleet(order)
    fault_tick = battery_fault["from_day"] * 24 * TICKS_PER_HOUR if battery_fault else None

    for robot in fleet:
        if robot.vendor not in ADAPTERS:
            raise ValueError(f"No adapter for vendor {robot.vendor} yet")

    records = []
    for tick in range(days * 24 * TICKS_PER_HOUR):
        when = SIM_START + timedelta(minutes=5 * tick)
        for robot in fleet:
            if tick == fault_tick and robot.robot_id == battery_fault["robot"]:
                robot.drain_per_hour = robot.drain_per_hour * battery_fault["drain_times"]
            robot.step()
            raw = ENCODERS[robot.vendor](robot, when)     # 1. robot reports in its own format
            record = ADAPTERS[robot.vendor](raw)          # 2. adapter translates it
            records.append(asdict(record))                # 3. keep the canonical record
    return pd.DataFrame(records)


def save_telemetry(telemetry, path=DB_FILE):
    """Store every canonical record in the database as a table called telemetry."""
    con = duckdb.connect(str(path))
    con.register("telemetry_df", telemetry)
    con.execute("CREATE OR REPLACE TABLE telemetry AS SELECT * FROM telemetry_df")
    con.close()


if __name__ == "__main__":
    random.seed(42)
    order = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}

    telemetry = run_pipeline(order, days=7)
    save_telemetry(telemetry)
    print(f"Translated and saved {len(telemetry):,} canonical records\n")