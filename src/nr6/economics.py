from dataclasses import dataclass

import pandas as pd


@dataclass
class Assumptions:
    """Every business assumption in one place, so each one can be changed and questioned."""

    fee_pct_of_price: float = 0.045      # monthly fee as a share of the robot's price
    autonomy_multiplier: float = 1.0     # 1 = catalogue fault rate; 0.5 = twice as reliable
    remote_fix_share: float = 0.7        # share of interventions fixed remotely
    remote_fix_cost: float = 6.0         # £ per remote fix (operator time)
    onsite_visit_cost: float = 110.0     # £ per engineer visit
    servicing_pct_per_year: float = 0.08 # yearly servicing as a share of price
    connectivity_per_month: float = 12.0 # £ per robot per month
    life_months: int = 48                # months before the robot is written off
    labour_share_replaced: float = 0.6   # share of the robot's hours a person would otherwise work
    loaded_wage_per_hour: float = 15.0   # £ per hour the customer pays a person, all-in


def robot_economics(price, hours_per_month, fault_rate, a=None):
    """Monthly money for one robot on one contract."""
    a = a or Assumptions()

    fee = price * a.fee_pct_of_price
    interventions = fault_rate * a.autonomy_multiplier * hours_per_month
    cost_per_intervention = (a.remote_fix_share * a.remote_fix_cost
                             + (1 - a.remote_fix_share) * a.onsite_visit_cost)
    intervention_cost = interventions * cost_per_intervention
    servicing = price * a.servicing_pct_per_year / 12

    running_cost = servicing + a.connectivity_per_month + intervention_cost   # cash out each month
    depreciation = price / a.life_months                                      # the robot wearing out
    margin = fee - running_cost - depreciation
    contribution = fee - running_cost                                         # cash left to repay the robot

    return {
        "fee": fee,
        "interventions": interventions,
        "intervention_cost": intervention_cost,
        "running_cost": running_cost,
        "depreciation": depreciation,
        "margin": margin,
        "payback_months": price / contribution if contribution > 0 else float("inf"),
        "customer_saving": hours_per_month * a.labour_share_replaced * a.loaded_wage_per_hour - fee,
    }


def catalogue_economics(catalogue, a=None):
    """robot_economics for every model in the catalogue, as one table."""
    rows = []
    for _, robot in catalogue.iterrows():
        result = robot_economics(robot["price_gbp"], robot["hours_per_month"], robot["fault_rate"], a)
        rows.append({"id": robot["id"], "name": robot["name"], "category": robot["category"],
                     "price_gbp": robot["price_gbp"], "price_status": robot["price_status"], **result})
    return pd.DataFrame(rows)