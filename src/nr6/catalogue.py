from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_FILE = PROJECT_ROOT / "data" / "catalogue.yaml"


def load_catalogue(path=CATALOGUE_FILE):
    """Read the catalogue file and return two tables: robots and sectors."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    robots = pd.DataFrame(raw["robots"])
    sectors = pd.DataFrame(raw["sectors"])
    return robots, sectors


if __name__ == "__main__":
    robots, sectors = load_catalogue()

    print("\nRobots with placeholder prices:")
    placeholders = robots[robots["price_status"] == "placeholder"]
    print(placeholders[["name", "price_gbp", "price_source"]])

    print("\nRobots that fit hospitality:")
    fits = sectors.loc[sectors["id"] == "hospitality", "fits"].iloc[0]
    hospitality_robots = robots[robots["category"].isin(fits)]
    print(hospitality_robots[["name", "category", "price_gbp"]])

    print("\nFleet cost:")
    prices = robots.set_index("id")["price_gbp"]
    order = {"pudu_cc1": 3, "keenon_t8": 2}

    total = 0
    for robot_id, quantity in order.items():
        line_cost = prices[robot_id] * quantity
        print(robot_id, quantity, "x", prices[robot_id], "=", line_cost)
        total = total + line_cost

    print("Total: £", total)
    