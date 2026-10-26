import random

from nr6.catalogue import load_catalogue
from nr6.db import save_run
from nr6.sim.robot import Robot, TICKS_PER_HOUR

DRAIN_PER_HOUR = 12   # placeholder: same for every robot until we add it to the catalogue


def build_fleet(order):
    """Create Robot objects from the catalogue, e.g. order = {"pudu_cc1": 3}."""
    robots_table, _ = load_catalogue()
    specs = robots_table.set_index("id")

    fleet = []
    number = 1
    for model_id, quantity in order.items():
        spec = specs.loc[model_id]
        for _ in range(quantity):
            robot_id = f"NR6-{number:04d}"
            fleet.append(Robot(robot_id, spec["name"], DRAIN_PER_HOUR, spec["fault_rate"]))
            number = number + 1
    return fleet


def run(fleet, days):
    """Move the whole fleet forward tick by tick and collect every event."""
    total_ticks = days * 24 * TICKS_PER_HOUR
    events = []
    for tick in range(total_ticks):
        for robot in fleet:
            event = robot.step()
            if event is not None:
                events.append((tick, robot.robot_id, robot.model, event))
    return events


if __name__ == "__main__":
    random.seed(42)   # same "random" results every run, so we can compare

    order = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}
    fleet = build_fleet(order)
    events = run(fleet, days=7)

    print(f"Simulated {len(fleet)} robots for 7 days: {len(events)} events\n")
    for robot in fleet:
        print(robot.status())

    total_hours = sum(robot.hours_worked for robot in fleet)
    total_interventions = sum(robot.interventions for robot in fleet)
    print(f"\nFleet: {total_interventions} interventions in {total_hours:.0f} robot-hours")
    print(f"Interventions per robot-hour: {total_interventions / total_hours:.3f}")
    
    save_run(events, fleet)
    
    