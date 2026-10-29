import math

import pytest

from nr6.economics import Assumptions, robot_economics

# Pudu CC1 from the catalogue: £18,000, 160 hours a month, 0.03 interventions per hour.
# Worked out by hand with the default assumptions:
#   fee            = 18,000 x 4.5%                    = 810.00
#   interventions  = 0.03 x 160                       = 4.8
#   per intervention = 70% x £6 + 30% x £110          = 37.20
#   intervention cost = 4.8 x 37.20                   = 178.56
#   servicing      = 18,000 x 8% / 12                 = 120.00
#   running cost   = 120 + 12 + 178.56                = 310.56
#   depreciation   = 18,000 / 48                      = 375.00
#   margin         = 810 - 310.56 - 375               = 124.44
#   payback        = 18,000 / (810 - 310.56)          = 36.04 months
#   customer saving = 160 x 60% x £15 - 810           = 630.00


def test_pudu_cc1_matches_hand_calculation():
    r = robot_economics(price=18000, hours_per_month=160, fault_rate=0.03)
    assert r["fee"] == pytest.approx(810)
    assert r["intervention_cost"] == pytest.approx(178.56)
    assert r["margin"] == pytest.approx(124.44)
    assert r["payback_months"] == pytest.approx(36.04, abs=0.01)
    assert r["customer_saving"] == pytest.approx(630)


def test_better_autonomy_halves_intervention_cost():
    normal = robot_economics(18000, 160, 0.03)
    better = robot_economics(18000, 160, 0.03, Assumptions(autonomy_multiplier=0.5))
    assert better["intervention_cost"] == pytest.approx(normal["intervention_cost"] / 2)
    assert better["margin"] > normal["margin"]


def test_loss_making_robot_never_pays_back():
    # Unitree G1: cheap to buy but needs a person very often
    r = robot_economics(price=10100, hours_per_month=80, fault_rate=0.35)
    assert r["margin"] < 0
    assert math.isinf(r["payback_months"])