from datetime import datetime, timezone

from nr6.adapters.canonical import CanonicalRecord

# How Pudu names things  ->  how NR6 names them
STATE_MAP = {
    "CLEANING": "WORKING",
    "IDLE": "IDLE",
    "CHARGING": "CHARGING",
    "ERROR": "FAULT",
    "OFFLINE": "OFFLINE",
}

FAULT_MAP = {
    "E201": "NAV_STUCK",
    "E105": "OBSTRUCTION",
    "E512": "BRUSH_JAM",
}


def to_canonical(raw):
    """Translate one raw Pudu message into an NR6 CanonicalRecord."""
    fault = None
    if raw["errCode"] is not None:
        fault = FAULT_MAP.get(raw["errCode"], "UNKNOWN")

    observed = datetime.fromtimestamp(raw["ts"] / 1000, tz=timezone.utc)

    return CanonicalRecord(
        robot_serial=raw["sn"],
        vendor="Pudu",
        state=STATE_MAP[raw["robotState"]],
        battery_pct=raw["power"],
        fault_code=fault,
        observed_at=observed.isoformat(),
        motor_temp_c=raw.get("motorTemp"),               # already in °C
    )