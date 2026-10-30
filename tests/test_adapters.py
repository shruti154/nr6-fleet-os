import pytest

from nr6.adapters import keenon, pudu, unitree
from nr6.adapters.canonical import CanonicalRecord

# The same moment as each brand reports it: stuck, 64% battery, 08:05 UTC on 19 Oct 2026
PUDU_MESSAGE = {"sn": "PD2024-1037", "robotState": "ERROR", "power": 64,
                "errCode": "E201", "ts": 1792397100000}
KEENON_MESSAGE = {"device_id": "KN-T8-0042", "status_code": 4, "battery_pct": 0.64,
                  "faults": [{"id": "0x31"}], "time": "2026-10-19T08:05:00Z"}
UNITREE_MESSAGE = {"robot_id": "G1-U1290", "fsm_mode": "damp", "bms": {"soc": 64},
                   "error_flags": 2, "t": 1792397100}


def test_pudu_translates_state_fault_and_time():
    record = pudu.to_canonical(PUDU_MESSAGE)
    assert record.state == "FAULT"
    assert record.fault_code == "NAV_STUCK"
    assert record.observed_at == "2026-10-19T08:05:00+00:00"


def test_keenon_battery_is_converted_to_percent():
    record = keenon.to_canonical(KEENON_MESSAGE)
    assert record.battery_pct == pytest.approx(64)


def test_all_three_vendors_agree():
    records = [
        pudu.to_canonical(PUDU_MESSAGE),
        keenon.to_canonical(KEENON_MESSAGE),
        unitree.to_canonical(UNITREE_MESSAGE),
    ]
    for record in records:
        assert record.state == "FAULT"
        assert record.battery_pct == pytest.approx(64)
        assert record.fault_code == "NAV_STUCK"
        assert record.observed_at == "2026-10-19T08:05:00+00:00"


def test_unknown_fault_code_does_not_crash():
    message = dict(PUDU_MESSAGE, errCode="E999")    # a code we have never seen
    record = pudu.to_canonical(message)
    assert record.fault_code == "UNKNOWN"


def test_impossible_battery_is_rejected():
    with pytest.raises(ValueError):
        CanonicalRecord(robot_serial="X", vendor="Test", state="WORKING",
                        battery_pct=150, fault_code=None,
                        observed_at="2026-10-19T08:05:00+00:00")
        


def test_keenon_fahrenheit_is_converted_to_celsius():
    message = dict(KEENON_MESSAGE, motor_temp_f=122.0)     # 122 °F is 50 °C
    record = keenon.to_canonical(message)
    assert record.motor_temp_c == pytest.approx(50.0)


def test_missing_temperature_is_allowed():
    record = pudu.to_canonical(PUDU_MESSAGE)               # this message has no temperature
    assert record.motor_temp_c is None