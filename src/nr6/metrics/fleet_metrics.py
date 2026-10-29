import duckdb

from nr6.db import DB_FILE

HOURS_PER_REPORT = 5 / 60   # each telemetry record covers 5 minutes

# Every telemetry row, plus a True/False column: did a new fault start on this report?
# LAG looks at the same robot's previous report. A fault "starts" when the robot is in
# FAULT now but was not in FAULT 5 minutes earlier.
WITH_FAULT_STARTS = """
    SELECT *,
           state = 'FAULT'
           AND COALESCE(LAG(state) OVER (PARTITION BY robot_serial ORDER BY observed_at), '') <> 'FAULT'
           AS fault_started
    FROM telemetry
"""


def run_query(sql):
    """Run one SQL query against the fleet database and return a pandas table."""
    con = duckdb.connect(str(DB_FILE), read_only=True)
    result = con.sql(sql).df()
    con.close()
    return result


def fleet_summary():
    """One row of headline numbers for the whole fleet."""
    return run_query(f"""
        WITH t AS ({WITH_FAULT_STARTS})
        SELECT COUNT(DISTINCT robot_serial)                                   AS robots,
               SUM(CASE WHEN state = 'WORKING' THEN 1 ELSE 0 END) * {HOURS_PER_REPORT} AS robot_hours,
               SUM(CASE WHEN fault_started THEN 1 ELSE 0 END)                 AS interventions,
               100 * AVG(CASE WHEN state = 'FAULT' THEN 0 ELSE 1 END)         AS availability_pct,
               MIN(observed_at)                                               AS period_start,
               MAX(observed_at)                                               AS period_end
        FROM t
    """)


def by_vendor():
    """Interventions per robot-hour and fault share for each vendor."""
    return run_query(f"""
        WITH t AS ({WITH_FAULT_STARTS})
        SELECT vendor,
               COUNT(DISTINCT robot_serial)                                   AS robots,
               SUM(CASE WHEN state = 'WORKING' THEN 1 ELSE 0 END) * {HOURS_PER_REPORT} AS robot_hours,
               SUM(CASE WHEN fault_started THEN 1 ELSE 0 END)                 AS interventions,
               100 * AVG(CASE WHEN state = 'FAULT' THEN 1 ELSE 0 END)         AS fault_pct
        FROM t
        GROUP BY vendor
        ORDER BY vendor
    """)


def interventions_by_day():
    """How many new faults each vendor's robots had on each day."""
    return run_query(f"""
        WITH t AS ({WITH_FAULT_STARTS})
        SELECT CAST(CAST(observed_at AS TIMESTAMPTZ) AS DATE) AS day,
               vendor,
               SUM(CASE WHEN fault_started THEN 1 ELSE 0 END) AS interventions
        FROM t
        GROUP BY day, vendor
        ORDER BY day, vendor
    """)


def robot_table():
    """One row per robot: its latest state plus its totals for the period."""
    return run_query(f"""
        WITH t AS ({WITH_FAULT_STARTS}),
        latest AS (
            SELECT robot_serial, state AS current_state, battery_pct AS battery
            FROM telemetry
            QUALIFY ROW_NUMBER() OVER (PARTITION BY robot_serial ORDER BY observed_at DESC) = 1
        )
        SELECT t.robot_serial                                                  AS robot,
               t.vendor,
               latest.current_state,
               latest.battery,
               SUM(CASE WHEN t.state = 'WORKING' THEN 1 ELSE 0 END) * {HOURS_PER_REPORT} AS hours_worked,
               SUM(CASE WHEN t.fault_started THEN 1 ELSE 0 END)                AS interventions,
               100 * AVG(CASE WHEN t.state = 'FAULT' THEN 0 ELSE 1 END)        AS availability_pct
        FROM t
        JOIN latest USING (robot_serial)
        GROUP BY t.robot_serial, t.vendor, latest.current_state, latest.battery
        ORDER BY interventions DESC
    """)
    
    

def daily_kpis():
    """The headline numbers worked out for each day, for the small trend lines."""
    return run_query(f"""
        WITH t AS ({WITH_FAULT_STARTS})
        SELECT CAST(LEFT(observed_at, 10) AS DATE)                             AS day,
               SUM(CASE WHEN state = 'WORKING' THEN 1 ELSE 0 END) * {HOURS_PER_REPORT} AS robot_hours,
               SUM(CASE WHEN fault_started THEN 1 ELSE 0 END)                 AS interventions,
               100 * AVG(CASE WHEN state = 'FAULT' THEN 0 ELSE 1 END)         AS availability_pct
        FROM t
        GROUP BY day
        ORDER BY day
    """)