from datetime import datetime, timezone

from nr6.adapters.canonical import CanonicalRecord

STATE_MAP = {
    "walk": "WORKING",
    "stand": "IDLE",
    "damp_charge": "CHARGING",
    "damp": "FAULT",
    "no_heartbeat": "OFFLINE",
}

# Unitree uses 0 for "no error"
FAULT_MAP = {
    2: "NAV_STUCK",
    64: "FALL_DETECTED",
}


def to_canonical(raw):
    """Translate one raw Unitree message into an NR6 CanonicalRecord."""
    fault = None
    if raw["error_flags"] != 0:
        fault = FAULT_MAP.get(raw["error_flags"], "UNKNOWN")

    observed = datetime.fromtimestamp(raw["t"], tz=timezone.utc)   # seconds, not milliseconds

    return CanonicalRecord(
        robot_serial=raw["robot_id"],
        vendor="Unitree",
        state=STATE_MAP[raw["fsm_mode"]],
        battery_pct=raw["bms"]["soc"],          # battery is tucked inside "bms"
        fault_code=fault,
        observed_at=observed.isoformat(),
    )