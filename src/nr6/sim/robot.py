import random

TICKS_PER_HOUR = 12              # one tick = 5 minutes
TICK_HOURS = 1 / TICKS_PER_HOUR
CHARGE_PER_HOUR = 40             # % of battery regained per hour on the dock


class Robot:
    """One robot in the NR6 fleet."""

    def __init__(self, robot_id, model, drain_per_hour, fault_rate):
        self.robot_id = robot_id
        self.model = model
        self.drain_per_hour = drain_per_hour
        self.fault_rate = fault_rate
        self.battery = 100.0
        self.state = "IDLE"
        self.hours_worked = 0.0
        self.interventions = 0
        self.fault_ticks_left = 0

    def step(self):
        """Move this robot forward by one 5-minute tick.
        Returns the name of an event if something happened, otherwise None."""

        # 1. A broken robot waits for a person to fix it
        if self.state == "FAULT":
            self.fault_ticks_left = self.fault_ticks_left - 1
            if self.fault_ticks_left <= 0:
                self.state = "IDLE"
                self.interventions = self.interventions + 1
                return "RESOLVED"
            return None

        # 2. A charging robot fills up, then goes back to work
        if self.state == "CHARGING":
            self.battery = min(100.0, self.battery + CHARGE_PER_HOUR * TICK_HOURS)
            if self.battery >= 100:
                self.state = "WORKING"
                return "BACK_TO_WORK"
            return None

        # 3. Otherwise the robot works for 5 minutes
        self.state = "WORKING"
        self.battery = self.battery - self.drain_per_hour * TICK_HOURS
        self.hours_worked = self.hours_worked + TICK_HOURS

        # Did it break down during these 5 minutes?
        if random.random() < self.fault_rate * TICK_HOURS:
            self.state = "FAULT"
            self.fault_ticks_left = random.randint(1, 6)   # fixed in 5 to 30 minutes
            return "FAULT"

        # Does it need to charge?
        if self.battery <= 20:
            self.state = "CHARGING"
            return "LOW_BATTERY"

        return None

    def status(self):
        """Return a one-line summary of this robot."""
        return (f"{self.robot_id} ({self.model}) | {self.state} | "
                f"battery {self.battery:.0f}% | worked {self.hours_worked:.1f} h | "
                f"interventions {self.interventions}")