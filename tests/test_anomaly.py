"""The anomaly detector must catch a fault we plant, and stay quiet on healthy robots."""
import random

from nr6.anomaly import drift_scores
from nr6.pipeline import run_pipeline

ORDER = {"pudu_cc1": 2, "keenon_t8": 2}
PLANTED = {"robot": "NR6-0003", "from_day": 4, "drain_times": 1.8}


def test_catches_planted_battery_fault():
    random.seed(1)
    scores = drift_scores(run_pipeline(ORDER, days=5, battery_fault=PLANTED))
    faulty = scores[scores["robot"] == PLANTED["robot"]]
    assert faulty.tail(12)["unusual"].any()
    assert (faulty.tail(12)["signal"] == "battery_drain").all()


def test_quiet_when_nothing_is_wrong():
    random.seed(1)
    scores = drift_scores(run_pipeline(ORDER, days=5))
    assert scores["unusual"].mean() < 0.02