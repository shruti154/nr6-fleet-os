from datetime import datetime

from nr6.adapters.canonical import CanonicalRecord

# Keenon sends its state as a number
STATE_MAP = {
    1: "IDLE",
    2: "WORKING",
    3: "CHARGING",
    4: "FAULT",
    5: "OFFLINE",
}

FAULT_MAP = {
    "0x31": "NAV_STUCK",
    "0x12": "OBSTRUCTION",
}


def to_canonical(raw):
    """Translate one raw Keenon message into an NR6 CanonicalRecord."""
    fault = None
    if raw["faults"]:                       # an empty list means no fault
        fault = FAULT_MAP.get(raw["faults"][0]["id"], "UNKNOWN")

    observed = datetime.fromisoformat(raw["time"].replace("Z", "+00:00"))

    return CanonicalRecord(
        robot_serial=raw["device_id"],
        vendor="Keenon",
        state=STATE_MAP[raw["status_code"]],
        battery_pct=raw["battery_pct"] * 100,   # Keenon sends 0 to 1
        fault_code=fault,
        observed_at=observed.isoformat(),
    )