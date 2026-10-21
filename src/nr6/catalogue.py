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
    print(robots[["name", "category", "price_gbp"]])