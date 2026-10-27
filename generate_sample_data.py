"""Generates flights.csv (SAMPLE data - NOT real airline records; airline names are fictional).
Run:  python generate_sample_data.py [number_of_rows]
Default is 30,000 flights. Use a bigger number (e.g. 1000000) on a laptop to demo 'big data'.
"""
import csv
import math
import random
import sys
from datetime import datetime, timedelta

random.seed(21)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30000

# code: (latitude, longitude, popularity, congestion factor, region)
AIRPORTS = {
    "DEL": (28.56, 77.10, 10, 1.4, "north"), "BOM": (19.09, 72.87, 10, 1.5, "coast"),
    "BLR": (13.20, 77.71, 9, 1.2, "south"), "MAA": (12.99, 80.17, 6, 1.0, "coast"),
    "HYD": (17.24, 78.43, 7, 1.0, "south"), "CCU": (22.65, 88.45, 6, 1.1, "coast"),
    "AMD": (23.07, 72.63, 4, 0.9, "west"), "PNQ": (18.58, 73.92, 4, 0.8, "west"),
    "GOI": (15.38, 73.83, 3, 0.9, "coast"), "COK": (10.15, 76.40, 3, 0.8, "coast"),
    "JAI": (26.82, 75.81, 3, 0.8, "north"), "LKO": (26.76, 80.88, 2, 0.8, "north"),
}
CODES = list(AIRPORTS)
POP = [AIRPORTS[c][2] for c in CODES]
# airline: (name, share, delay factor)  - fictional
AIRLINES = [("BlueWing", 45, 0.85), ("SkyJet", 22, 1.2), ("AirNova", 15, 1.0), ("FlyExpress", 12, 1.35), ("CloudAir", 6, 0.8)]
AL_NAMES = [a[0] for a in AIRLINES]
AL_W = [a[1] for a in AIRLINES]
AL_F = {a[0]: a[2] for a in AIRLINES}
AL_CODE = {"BlueWing": "BW", "SkyJet": "SJ", "AirNova": "AN", "FlyExpress": "FX", "CloudAir": "CA"}
HOUR_W = [1, 1, 1, 1, 2, 4, 7, 8, 8, 6, 5, 5, 5, 5, 5, 6, 7, 8, 8, 7, 6, 4, 3, 2]
START = datetime(2026, 1, 1)
DAYS = 273          # 1 Jan - 30 Sep 2026 (includes winter fog and monsoon)
FMT = "%Y-%m-%d %H:%M:%S"


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (AIRPORTS[a][0], AIRPORTS[a][1], AIRPORTS[b][0], AIRPORTS[b][1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


rows = []
for _ in range(N):
    day = START + timedelta(days=random.randrange(DAYS))
    hour = random.choices(range(24), weights=HOUR_W)[0]
    o = random.choices(CODES, weights=POP)[0]
    d = o
    while d == o:
        d = random.choices(CODES, weights=POP)[0]
    airline = random.choices(AL_NAMES, weights=AL_W)[0]
    dist = round(km(o, d) * 1.05, 1)
    dur = int(round((dist / 760 * 60 + 28) / 5) * 5)
    sdep = day.replace(hour=hour, minute=random.randrange(0, 60, 5), second=0)
    sarr = sdep + timedelta(minutes=dur)

    month, region = day.month, AIRPORTS[o][4]
    hour_f = 1 + 0.07 * max(0, hour - 6)                    # delays build up through the day
    season_f = 1.0
    if month == 1 and region == "north":
        season_f = 2.0                                      # winter fog
    elif 6 <= month <= 9:
        season_f = 1.8 if region in ("coast", "west") else 1.3   # monsoon
    p = min(0.85, 0.11 * AIRPORTS[o][3] * AL_F[airline] * hour_f * season_f)

    status, reason, dep_delay, arr_delay = "Completed", "", 0, 0
    if random.random() < p:
        w_weather = 3.0 * season_f if season_f > 1 else 0.6
        w_atc = 2.0 * AIRPORTS[o][3]
        w_air = 2.0 * AL_F[airline]
        w_late = 0.8 + 0.5 * max(0, hour - 8)
        reason = random.choices(["Weather", "ATC / Congestion", "Airline", "Late Aircraft", "Security"],
                                weights=[w_weather, w_atc, w_air, w_late, 0.15])[0]
        dep_delay = int(15 + random.expovariate(1 / 32))
        dep_delay = min(dep_delay, 600)
        if reason == "Weather" and random.random() < 0.10:
            status = "Cancelled"
    else:
        dep_delay = int(random.gauss(-2, 6))
        if random.random() < 0.004:
            status, reason = "Cancelled", "Airline"
    if status == "Completed":
        arr_delay = int(dep_delay + random.gauss(-4 - dist / 1000 * 2, 6))
        arr_delay = max(arr_delay, -25)
        adep, aarr = sdep + timedelta(minutes=dep_delay), sarr + timedelta(minutes=arr_delay)
        if aarr <= adep:
            aarr = adep + timedelta(minutes=max(30, dur - 10))
        a1, a2 = adep.strftime(FMT), aarr.strftime(FMT)
    else:
        a1 = a2 = ""
    fno = f"{AL_CODE[airline]}{random.randint(100, 899)}"
    rows.append([day.strftime("%Y-%m-%d"), airline, fno, o, d, sdep.strftime(FMT), sarr.strftime(FMT), a1, a2, dist, status, reason, sdep])

rows.sort(key=lambda r: r[-1])
header = ["flight_id", "flight_date", "airline", "flight_no", "origin", "destination", "scheduled_dep",
          "scheduled_arr", "actual_dep", "actual_arr", "distance_km", "status", "delay_reason"]
with open("flights.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    first = None
    for i, r in enumerate(rows, 1):
        line = [f"FL{i:07d}"] + r[:-1]
        if i == 1:
            first = line
        w.writerow(line)
    # deliberately bad rows so the cleaning step has something to do
    w.writerow(first)                                                                                                         # duplicate flight_id
    w.writerow(["FX00002", "2026-03-05", "SkyJet", "SJ210", "DEL", "DEL", "2026-03-05 09:00:00", "2026-03-05 11:00:00", "2026-03-05 09:05:00", "2026-03-05 11:02:00", 900, "Completed", ""])   # same origin and destination
    w.writerow(["FX00003", "2026-03-05", "AirNova", "AN310", "BOM", "BLR", "not-a-time", "2026-03-05 12:00:00", "2026-03-05 10:05:00", "2026-03-05 12:02:00", 840, "Completed", ""])   # invalid time
    w.writerow(["FX00004", "2026-03-06", "BlueWing", "BW410", "MAA", "HYD", "2026-03-06 08:00:00", "2026-03-06 09:15:00", "2026-03-06 08:05:00", "2026-03-06 09:20:00", -500, "Completed", ""])  # negative distance
    w.writerow(["FX00005", "2026-03-06", "", "XX510", "CCU", "DEL", "2026-03-06 10:00:00", "2026-03-06 12:10:00", "2026-03-06 10:05:00", "2026-03-06 12:15:00", 1300, "Completed", ""])    # missing airline
    w.writerow(["FX00006", "2026-03-07", "FlyExpress", "FX610", "PNQ", "GOI", "2026-03-07 14:00:00", "2026-03-07 13:00:00", "2026-03-07 14:05:00", "2026-03-07 13:10:00", 400, "Completed", ""])  # arrives before it departs
    w.writerow(["FX00007", "2026-03-07", "CloudAir", "CA710", "AMD", "JAI", "2026-03-07 07:00:00", "2026-03-07 08:30:00", "2026-03-07 07:10:00", "2026-03-09 18:30:00", 560, "Completed", "Airline"])   # absurd 3,000-minute delay
    w.writerow(["FX00008", "2026-03-08", "BlueWing", "BW810", "LKO", "DEL", "2026-03-08 16:00:00", "2026-03-08 17:10:00", "2026-03-08 16:05:00", "2026-03-08 17:12:00", "abc", "Completed", ""])  # non-numeric distance
print(f"flights.csv written with {len(rows) + 8} rows")
