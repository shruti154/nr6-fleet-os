from nr6.adapters import pudu

# A message exactly as a Pudu robot might send it
pudu_message = {
    "sn": "PD2024-1037",
    "robotState": "ERROR",
    "power": 64,
    "errCode": "E201",
    "ts": 1792397100000,
}

print("RAW (Pudu's own format):")
print(pudu_message)

print("\nCANONICAL (NR6's standard format):")
print(pudu.to_canonical(pudu_message))