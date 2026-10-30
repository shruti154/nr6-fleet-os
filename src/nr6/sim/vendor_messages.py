from datetime import datetime, timezone

from nr6.adapters import keenon, pudu, unitree

SIM_START = datetime(2026, 10, 19, 7, 0, tzinfo=timezone.utc)   # the simulated Monday morning


def reverse(mapping):
    """Flip a translation dictionary: NR6's word -> the vendor's word."""
    return {nr6_word: vendor_word for vendor_word, nr6_word in mapping.items()}


# Each robot "speaks" its own brand's format, so we need the vendor's words
PUDU_STATES, PUDU_FAULTS = reverse(pudu.STATE_MAP), reverse(pudu.FAULT_MAP)
KEENON_STATES, KEENON_FAULTS = reverse(keenon.STATE_MAP), reverse(keenon.FAULT_MAP)
UNITREE_STATES, UNITREE_FAULTS = reverse(unitree.STATE_MAP), reverse(unitree.FAULT_MAP)


def temperature(robot):
    """The robot's motor temperature in °C, or None if we don't have one."""
    temp = getattr(robot, "motor_temp", None)
    return None if temp is None else round(temp, 1)


def fahrenheit(celsius):
    return None if celsius is None else round(celsius * 9 / 5 + 32, 1)


def pudu_message(robot, when):
    return {
        "sn": robot.robot_id,
        "robotState": PUDU_STATES[robot.state],
        "power": round(robot.battery),
        "errCode": PUDU_FAULTS[robot.fault_code] if robot.fault_code else None,
        "ts": int(when.timestamp() * 1000),            # milliseconds
        "motorTemp": temperature(robot),               # °C
    }


def keenon_message(robot, when):
    return {
        "device_id": robot.robot_id,
        "status_code": KEENON_STATES[robot.state],
        "battery_pct": round(robot.battery) / 100,     # 0 to 1
        "faults": [{"id": KEENON_FAULTS[robot.fault_code]}] if robot.fault_code else [],
        "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "motor_temp_f": fahrenheit(temperature(robot)),  # Keenon uses Fahrenheit
    }


def unitree_message(robot, when):
    return {
        "robot_id": robot.robot_id,
        "fsm_mode": UNITREE_STATES[robot.state],
        "bms": {"soc": round(robot.battery)},
        "error_flags": UNITREE_FAULTS[robot.fault_code] if robot.fault_code else 0,
        "t": int(when.timestamp()),                    # seconds
        "motor_temp_max_c": temperature(robot),        # °C
    }


# Which "language" each brand speaks
ENCODERS = {
    "Pudu": pudu_message,
    "Keenon": keenon_message,
    "Unitree": unitree_message,
}