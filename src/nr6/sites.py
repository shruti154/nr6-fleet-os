"""Customers, sites and the inventory: which robot is at which site.

Telemetry tells us what each robot did. The inventory tells us where each
robot is and who it works for. Together they give customer -> site -> robot.
"""
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from nr6.catalogue import load_catalogue
from nr6.db import DB_FILE
from nr6.sim.fleet import build_fleet

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CUSTOMERS_FILE = PROJECT_ROOT / "data" / "customers.yaml"


def load_sites(path=CUSTOMERS_FILE):
    """Read customers.yaml and return one row per site."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    rows = []
    for customer in raw["customers"]:
        for site in customer["sites"]:
            rows.append({
                "site_id": site["id"],
                "site": site["name"],
                "customer": customer["name"],
                "sector": site["sector"],
                "sla_uptime_pct": site["sla_uptime_pct"],
            })
    return pd.DataFrame(rows)


def build_inventory(order):
    """Place every robot in the fleet at a site that suits it.

    A robot suits a site when its category (Cleaning, Delivery...) is in the
    'fits' list of the site's sector. Among suitable sites, the robot goes to
    the one with the fewest robots so far, so sites fill up evenly."""
    robots_table, sectors = load_catalogue()
    category_of = robots_table.set_index("name")["category"]
    fits = sectors.set_index("id")["fits"]
    sites = load_sites()

    robots_at = {site_id: 0 for site_id in sites["site_id"]}
    rows = []
    for robot in build_fleet(order):
        category = category_of[robot.model]
        suitable = [s for s in sites.itertuples() if category in fits[s.sector]]
        candidates = suitable or list(sites.itertuples())      # nothing suits: use any site
        chosen = min(candidates, key=lambda s: robots_at[s.site_id])
        robots_at[chosen.site_id] += 1
        rows.append({
            "robot_serial": robot.robot_id,
            "model": robot.model,
            "category": category,
            "site_id": chosen.site_id,
        })
    return pd.DataFrame(rows)


def save_inventory(order, path=DB_FILE):
    """Store the sites and the inventory in the database as two tables."""
    sites = load_sites()
    inventory = build_inventory(order)
    con = duckdb.connect(str(path))
    con.register("sites_df", sites)
    con.register("inventory_df", inventory)
    con.execute("CREATE OR REPLACE TABLE sites AS SELECT * FROM sites_df")
    con.execute("CREATE OR REPLACE TABLE inventory AS SELECT * FROM inventory_df")
    con.close()
    return inventory


if __name__ == "__main__":
    order = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}

    print("Sites:")
    print(load_sites().to_string(index=False))

    inventory = save_inventory(order)
    print("\nInventory (which robot is where):")
    print(inventory.merge(load_sites()[["site_id", "site"]], on="site_id")
          .drop(columns="site_id").to_string(index=False))
    print(f"\nSaved {len(inventory)} robots across {inventory['site_id'].nunique()} sites to the database")