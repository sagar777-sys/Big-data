# ✈️ Flight Delay Analytics (Apache Spark + Streamlit)

Big-data project: analyses flight records with **Apache Spark (PySpark)** to find *when, where and why flights are delayed*, and shows the results in an interactive **Streamlit** dashboard.

**Why Spark and not Hive?** Hive needs a Hadoop cluster and a Hive server, so it cannot be hosted on Streamlit Community Cloud. PySpark runs in local mode with just Java, scales to a cluster without changing the code, and lets the whole project be written in Python.

## Features
- Reads a flights CSV with PySpark and **cleans** it (8 validation rules, duplicates removed).
- Derives departure delay, arrival delay, hour, day of week, month and route.
- Computes delay rate, average delay and cancellation rate by **airline, airport, route, hour, day, month**.
- **Delay causes**: weather, ATC / congestion, airline, late aircraft, security.
- Interactive dashboard: filters, KPI cards, charts, heat map, CSV upload and report downloads.
- A flight is **delayed** when it arrives 15 minutes or more after its scheduled arrival.

## Spark pipeline
1. Read CSV (all columns as text) → 2. Clean and validate → 3. Derive new columns → 4. `groupBy` + aggregate → 5. Small summary tables → 6. Streamlit charts.

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard |
| `spark_engine.py` | PySpark reading, cleaning and analysis (core of the project) |
| `pandas_engine.py` | Same logic in pandas, used only if Spark/Java cannot start on the host |
| `common.py` | Constants and helpers shared by both engines |
| `generate_sample_data.py` | Creates `flights.csv` (default 30,000 rows; pass a number for more) |
| `flights.csv` | Sample data (generated, **not real**; airline names are fictional) |
| `check_engines.py` | Optional test: Spark and pandas results must match |
| `requirements.txt`, `packages.txt` | Python packages, and Java for the hosting server |
| `Dockerfile` | Optional, for Docker hosts such as Render |

## CSV columns
`flight_id, flight_date, airline, flight_no, origin, destination, scheduled_dep, scheduled_arr, actual_dep, actual_arr, distance_km, status, delay_reason`
Times use `YYYY-MM-DD HH:MM:SS`. `status` is `Completed` or `Cancelled` (cancelled flights have empty actual times).

## Cleaning rules
A row is removed if: flight id or airline or airport is blank; origin = destination; scheduled times are invalid or arrival is not after departure; distance is not between 0 and 5,000 km; status is not Completed/Cancelled; a completed flight has missing or impossible actual times, or a delay beyond −120 to +1,440 minutes; or the flight id is duplicated.

## Run locally
```bash
pip install -r requirements.txt     # Java 17+ must also be installed
python generate_sample_data.py      # optional: recreate flights.csv (try 1000000 for a big-data demo)
streamlit run app.py
python check_engines.py             # optional: compare Spark vs pandas
```

## Upload to GitHub
```bash
git init
git add .
git commit -m "Flight delay analytics with Spark"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```
(Create the empty repository on github.com first.)

## Host on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** → choose your repository, branch `main`, main file `app.py`.
3. Click **Deploy**. It installs `requirements.txt` and Java from `packages.txt` (first start takes a few minutes).

## Limitations
Spark runs in local mode on one machine; the data is generated; analysis is descriptive (no prediction); the free host has limited memory, so run very large files locally.

## Future scope
Spark MLlib delay prediction, Structured Streaming for live flights, weather data, map view, database storage.
