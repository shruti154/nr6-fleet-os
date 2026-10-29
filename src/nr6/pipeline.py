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


def run_pipeline(order, days):
    """Simulate the fleet. Every 5 minutes, each robot sends a message in its own
    brand's format, and the matching adapter translates it into a canonical record."""
    fleet = build_fleet(order)

    for robot in fleet:
        if robot.vendor not in ADAPTERS:
            raise ValueError(f"No adapter for vendor {robot.vendor} yet")

    records = []
    for tick in range(days * 24 * TICKS_PER_HOUR):
        when = SIM_START + timedelta(minutes=5 * tick)
        for robot in fleet:
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

    con = duckdb.connect(str(DB_FILE), read_only=True)
    print("Faults seen in telemetry, by vendor and fault type:")
    print(con.sql("""
        SELECT vendor, fault_code, COUNT(*) AS reports
        FROM telemetry
        WHERE state = 'FAULT'
        GROUP BY vendor, fault_code
        ORDER BY reports DESC
    """).df())

    print("\nShare of time spent in each state, by vendor:")
    print(con.sql("""
        SELECT vendor,
               ROUND(100 * AVG(CASE WHEN state = 'WORKING'  THEN 1 ELSE 0 END), 1) AS working_pct,
               ROUND(100 * AVG(CASE WHEN state = 'CHARGING' THEN 1 ELSE 0 END), 1) AS charging_pct,
               ROUND(100 * AVG(CASE WHEN state = 'FAULT'    THEN 1 ELSE 0 END), 1) AS fault_pct
        FROM telemetry
        GROUP BY vendor
        ORDER BY fault_pct DESC
    """).df())
    con.close()