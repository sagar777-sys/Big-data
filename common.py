"""Shared constants and helpers used by BOTH engines (Spark and pandas)."""
import numpy as np
import pandas as pd

REQUIRED = ["flight_id", "flight_date", "airline", "flight_no", "origin", "destination",
            "scheduled_dep", "scheduled_arr", "actual_dep", "actual_arr",
            "distance_km", "status", "delay_reason"]
TS_FORMAT = "yyyy-MM-dd HH:mm:ss"          # Spark pattern
PD_FORMAT = "%Y-%m-%d %H:%M:%S"            # pandas pattern
DELAY_MINUTES = 15                          # arrival delay of 15+ minutes = "delayed" (industry standard)
DOW = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}   # Spark dayofweek: 1 = Sunday
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MIN_ROUTE_FLIGHTS = 20                      # a route needs this many flights to be ranked

# (upper limit in minutes, label) - last bucket has no limit
BUCKETS = [(15, "On time (under 15 min)"), (30, "15-30 min"), (60, "30-60 min"),
           (120, "1-2 hours"), (None, "Over 2 hours")]
BUCKET_LABELS = [b[1] for b in BUCKETS]


def finalize(p):
    """Turn raw counts into rates. Input columns: flights, completed, cancelled, delayed, avg_*."""
    p = p.copy()
    for c in ["flights", "completed", "cancelled", "delayed"]:
        p[c] = p[c].fillna(0).astype(int)
    for c in ["avg_arr_delay", "avg_dep_delay"]:
        p[c] = p[c].fillna(0.0).astype(float).round(2)
    p["delay_rate"] = np.where(p["completed"] > 0, p["delayed"] / p["completed"].replace(0, 1) * 100, 0.0).round(2)
    p["cancel_rate"] = np.where(p["flights"] > 0, p["cancelled"] / p["flights"].replace(0, 1) * 100, 0.0).round(2)
    return p


def kpi_from(p):
    """One-row aggregate -> dict (zeros if no flights match the filters)."""
    if len(p) == 0:
        return {"flights": 0, "completed": 0, "cancelled": 0, "delayed": 0, "avg_arr_delay": 0.0,
                "avg_dep_delay": 0.0, "delay_rate": 0.0, "cancel_rate": 0.0, "on_time_rate": 0.0}
    r = p.iloc[0]
    k = {c: float(r[c]) for c in p.columns}
    for c in ["flights", "completed", "cancelled", "delayed"]:
        k[c] = int(r[c])
    k["on_time_rate"] = round(100.0 - k["delay_rate"], 2) if k["completed"] else 0.0
    return k


def finish_tables(kpi_df, by_airline, by_airport, by_hour, by_month, by_date, heat, routes, reasons, buckets):
    """Sort / tidy the tables so both engines return exactly the same shapes."""
    heat = heat.copy()
    heat["day"] = heat["dow"].map(DOW)
    heat = heat[["day", "hour", "flights", "delay_rate"]]
    routes = routes[routes["flights"] >= MIN_ROUTE_FLIGHTS].sort_values(
        ["avg_arr_delay", "flights"], ascending=[False, False]).head(10).reset_index(drop=True)
    buckets = buckets.set_index("bucket").reindex(BUCKET_LABELS).fillna(0).reset_index()
    buckets["flights"] = buckets["flights"].astype(int)
    return {
        "kpi": kpi_from(kpi_df),
        "by_airline": by_airline.sort_values("delay_rate", ascending=False).reset_index(drop=True),
        "by_airport": by_airport.sort_values("flights", ascending=False).reset_index(drop=True),
        "by_hour": by_hour.sort_values("hour").reset_index(drop=True),
        "by_month": by_month.sort_values("month").reset_index(drop=True),
        "by_date": by_date.sort_values("date").reset_index(drop=True),
        "heat": heat,
        "routes": routes,
        "reasons": reasons.sort_values("delayed", ascending=False).reset_index(drop=True),
        "buckets": buckets,
    }
