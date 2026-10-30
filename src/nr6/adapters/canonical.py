from dataclasses import dataclass

VALID_STATES = {"WORKING", "IDLE", "CHARGING", "FAULT", "OFFLINE"}


@dataclass
class CanonicalRecord:
    """The one standard way NR6 describes any robot, whatever its brand."""

    robot_serial: str
    vendor: str
    state: str               # one of VALID_STATES
    battery_pct: float       # always 0 to 100
    fault_code: str | None   # NR6's own fault name, or None if no fault
    observed_at: str         # date and time in ISO 8601 format, UTC
    motor_temp_c: float | None = None   # motor temperature in °C, if the vendor reports it

    def __post_init__(self):
        """Runs automatically after a record is created: reject anything invalid."""
        if self.state not in VALID_STATES:
            raise ValueError(f"Unknown state: {self.state}")
        if not 0 <= self.battery_pct <= 100:
            raise ValueError(f"Battery out of range: {self.battery_pct}")