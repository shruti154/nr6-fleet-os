from nr6.adapters import keenon, pudu, unitree

# The SAME moment, as three different brands would report it:
# robot stuck, 64% battery, 08:05 UTC on 19 October 2026

pudu_message = {
    "sn": "PD2024-1037",
    "robotState": "ERROR",
    "power": 64,
    "errCode": "E201",
    "ts": 1792397100000,
}

keenon_message = {
    "device_id": "KN-T8-0042",
    "status_code": 4,
    "battery_pct": 0.64,
    "faults": [{"id": "0x31"}],
    "time": "2026-10-19T08:05:00Z",
}

unitree_message = {
    "robot_id": "G1-U1290",
    "fsm_mode": "damp",
    "bms": {"soc": 64, "cycles": 112},
    "error_flags": 2,
    "t": 1792397100,
}

for adapter, message in [(pudu, pudu_message), (keenon, keenon_message), (unitree, unitree_message)]:
    record = adapter.to_canonical(message)
    print("RAW:      ", message)
    print("CANONICAL:", record.vendor, "|", record.state, "|", record.battery_pct, "% |",
          record.fault_code, "|", record.observed_at)
    print()