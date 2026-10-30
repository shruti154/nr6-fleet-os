import random

TICKS_PER_HOUR = 12              # one tick = 5 minutes
TICK_HOURS = 1 / TICKS_PER_HOUR
CHARGE_PER_HOUR = 40             # % of battery regained per hour on the dock


class Robot:
    """One robot in the NR6 fleet."""

    def __init__(self, robot_id, model, drain_per_hour, fault_rate,
                 vendor="Generic", possible_faults=("NAV_STUCK", "OBSTRUCTION")):
        self.robot_id = robot_id
        self.model = model
        self.vendor = vendor
        self.possible_faults = possible_faults
        self.drain_per_hour = drain_per_hour
        self.fault_rate = fault_rate
        self.battery = 100.0
        self.state = "IDLE"
        self.hours_worked = 0.0
        self.interventions = 0
        self.fault_ticks_left = 0
        self.fault_code = None
        # Wear: 0 = like new, 1 = badly worn. Each robot wears at its own speed.
        self.wear = random.uniform(0.0, 0.3)
        self.wear_per_hour = random.uniform(0.004, 0.012)
        self.motor_temp = 35.0

    def step(self):
        """Move this robot forward by one 5-minute tick.
        Returns the name of an event if something happened, otherwise None."""

        # Motor temperature: a worn robot runs hotter. This is the early warning signal.
        working_heat = 6 if self.state == "WORKING" else 0
        self.motor_temp = 34 + 28 * self.wear + working_heat + random.gauss(0, 1.5)

        # 1. A broken robot waits for a person to fix it
        if self.state == "FAULT":
            self.fault_ticks_left = self.fault_ticks_left - 1
            if self.fault_ticks_left <= 0:
                self.state = "IDLE"
                self.fault_code = None
                self.interventions = self.interventions + 1
                self.wear = self.wear * 0.4          # the repair also services the robot
                return "RESOLVED"
            return None

        # 2. A charging robot fills up, then goes back to work
        if self.state == "CHARGING":
            self.battery = min(100.0, self.battery + CHARGE_PER_HOUR * TICK_HOURS)
            if self.battery >= 100:
                self.state = "WORKING"
                return "BACK_TO_WORK"
            return None

        # 3. Otherwise the robot works for 5 minutes, and wears a little
        self.state = "WORKING"
        self.battery = self.battery - self.drain_per_hour * TICK_HOURS
        self.hours_worked = self.hours_worked + TICK_HOURS
        self.wear = min(1.0, self.wear + self.wear_per_hour * TICK_HOURS)

        # Did it break down? A worn robot is much more likely to.
        chance = self.fault_rate * TICK_HOURS * (0.6 + 6 * self.wear ** 2)
        if random.random() < chance:
            self.state = "FAULT"
            self.fault_code = random.choice(self.possible_faults)
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