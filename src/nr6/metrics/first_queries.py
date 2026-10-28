import duckdb

from nr6.db import DB_FILE

con = duckdb.connect(str(DB_FILE), read_only=True)

print("\n1. A first look at the events table:")
print(con.sql("SELECT * FROM events LIMIT 5").df())

print("\n2. How many of each event type?")
print(con.sql("""
    SELECT event, COUNT(*) AS how_many
    FROM events
    GROUP BY event
    ORDER BY how_many DESC
""").df())

print("\n3. Interventions per robot-hour, by model:")
print(con.sql("""
    SELECT model,
           SUM(interventions) AS interventions,
           ROUND(SUM(hours_worked)) AS hours,
           ROUND(SUM(interventions) / SUM(hours_worked), 3) AS per_robot_hour
    FROM robots
    GROUP BY model
    ORDER BY per_robot_hour DESC
""").df())

print("\n4. Which models had the most faults?")
print(con.sql("""
    SELECT model, COUNT(*) AS faults
    FROM events
    WHERE event = 'FAULT'
    GROUP BY model
    ORDER BY faults DESC
""").df())

con.close()