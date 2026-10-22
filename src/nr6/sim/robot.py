class Robot:
    """One robot in the NR6 fleet."""

    def __init__(self, robot_id, model, drain_per_hour):
        self.robot_id = robot_id
        self.model = model
        self.drain_per_hour = drain_per_hour
        self.battery = 100.0
        self.state = "IDLE"
        self.hours_worked = 0.0

    def work(self, hours):
        """Work for a number of hours, using up battery."""
        self.state = "WORKING"
        self.battery = self.battery - self.drain_per_hour * hours
        self.hours_worked = self.hours_worked + hours
        if self.battery <= 20:
            self.state = "CHARGING"

    def charge(self):
        """Recharge to full and go back to idle."""
        self.battery = 100.0
        self.state = "IDLE"

    def status(self):
        """Return a one-line summary of this robot."""
        return f"{self.robot_id} ({self.model}) | {self.state} | battery {self.battery:.0f}% | worked {self.hours_worked} h"


if __name__ == "__main__":
    robot = Robot("NR6-0001", "Pudu CC1", drain_per_hour=20)
    print(robot.status())

    robot.work(2)
    print(robot.status())

    robot.work(2)
    print(robot.status())

    robot.charge()
    print(robot.status())
    
    robot2 = Robot("NR6-0002", "Keenon T8", drain_per_hour=10)
    robot2.work(3)
    print(robot2.status())