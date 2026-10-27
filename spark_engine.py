"""Apache Spark (PySpark) engine: reads, cleans and analyses the flight data."""
import os
import sys

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

import common as C

NAME = "Apache Spark (PySpark)"
_spark = None


def get_spark():
    global _spark
    if _spark is None:
        os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
        _spark = (
            SparkSession.builder.appName("FlightDelayAnalytics")
            .master("local[2]")                                   # local mode: 2 CPU cores, no cluster needed
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.driver.memory", "512m")
            .config("spark.sql.ansi.enabled", "false")            # bad values become NULL instead of errors
            .getOrCreate()
        )
        _spark.sparkContext.setLogLevel("ERROR")
    return _spark


def _ts(col):
    return F.to_timestamp(F.trim(col), C.TS_FORMAT)


def load_and_clean(path):
    """Returns (cleaned_spark_df, stats_dict)."""
    spark = get_spark()
    raw = spark.read.option("header", True).option("quote", '"').csv(path)      # everything as string first
    raw = raw.toDF(*[c.strip().lower() for c in raw.columns])
    missing = [c for c in C.REQUIRED if c not in raw.columns]
    if missing:
        raise ValueError("CSV is missing columns: " + ", ".join(missing))

    rows_in = raw.count()
    df = raw.select(
        F.trim(F.coalesce(F.col("flight_id"), F.lit(""))).alias("flight_id"),
        F.trim(F.coalesce(F.col("airline"), F.lit(""))).alias("airline"),
        F.trim(F.coalesce(F.col("flight_no"), F.lit(""))).alias("flight_no"),
        F.upper(F.trim(F.coalesce(F.col("origin"), F.lit("")))).alias("origin"),
        F.upper(F.trim(F.coalesce(F.col("destination"), F.lit("")))).alias("destination"),
        _ts("scheduled_dep").alias("sched_dep"),
        _ts("scheduled_arr").alias("sched_arr"),
        _ts("actual_dep").alias("act_dep"),
        _ts("actual_arr").alias("act_arr"),
        F.trim("distance_km").cast("double").alias("distance_km"),
        F.lower(F.trim(F.coalesce(F.col("status"), F.lit("")))).alias("status"),
        F.when(F.trim(F.coalesce(F.col("delay_reason"), F.lit(""))) == "", F.lit("Unspecified"))
         .otherwise(F.trim(F.col("delay_reason"))).alias("delay_reason"),
    )
    done = F.col("status") == "completed"
    df = (df.withColumn("dep_delay", F.when(done, (F.unix_timestamp("act_dep") - F.unix_timestamp("sched_dep")) / 60.0))
            .withColumn("arr_delay", F.when(done, (F.unix_timestamp("act_arr") - F.unix_timestamp("sched_arr")) / 60.0)))

    base = ((F.col("flight_id") != "") & (F.col("airline") != "") & (F.col("origin") != "")
            & (F.col("destination") != "") & (F.col("origin") != F.col("destination"))
            & F.col("sched_dep").isNotNull() & F.col("sched_arr").isNotNull()
            & (F.col("sched_arr") > F.col("sched_dep"))
            & (F.col("distance_km") > 0) & (F.col("distance_km") <= 5000)
            & F.col("status").isin("completed", "cancelled"))
    ok_done = (F.col("act_dep").isNotNull() & F.col("act_arr").isNotNull() & (F.col("act_arr") > F.col("act_dep"))
               & F.col("dep_delay").between(-120, 1440) & F.col("arr_delay").between(-120, 1440))
    df = df.filter(base & ((F.col("status") == "cancelled") | ok_done)).dropDuplicates(["flight_id"])

    df = (df.withColumn("completed", F.when(done, 1).otherwise(0))
            .withColumn("cancelled", F.when(F.col("status") == "cancelled", 1).otherwise(0))
            .withColumn("delayed", F.when((F.col("status") == "completed") & (F.col("arr_delay") >= C.DELAY_MINUTES), 1).otherwise(0))
            .withColumn("date", F.to_date("sched_dep"))
            .withColumn("hour", F.hour("sched_dep"))
            .withColumn("dow", F.dayofweek("sched_dep"))
            .withColumn("month", F.date_format("sched_dep", "yyyy-MM"))
            .withColumn("route", F.concat_ws(" → ", "origin", "destination"))
            .cache())
    rows_out = df.count()
    return df, {"rows_in": rows_in, "rows_out": rows_out, "rows_dropped": rows_in - rows_out}


def get_options(df):
    airlines = sorted(r[0] for r in df.select("airline").distinct().collect())
    origins = sorted(r[0] for r in df.select("origin").distinct().collect())
    b = df.agg(F.min("date"), F.max("date")).collect()[0]
    return airlines, origins, b[0], b[1]


def _agg(f, *keys):
    aggs = [F.count("*").alias("flights"), F.sum("completed").alias("completed"),
            F.sum("cancelled").alias("cancelled"), F.sum("delayed").alias("delayed"),
            F.avg("arr_delay").alias("avg_arr_delay"), F.avg("dep_delay").alias("avg_dep_delay")]
    out = f.groupBy(*keys).agg(*aggs) if keys else f.agg(*aggs)
    return C.finalize(out.toPandas())


def analyze(df, start, end, airlines, origins, hmin, hmax):
    f = df.filter(
        (F.col("date") >= F.lit(start)) & (F.col("date") <= F.lit(end))
        & F.col("airline").isin(airlines) & F.col("origin").isin(origins)
        & F.col("hour").between(hmin, hmax)
    )
    bad = f.filter((F.col("delayed") == 1) | (F.col("cancelled") == 1))
    a = F.col("arr_delay")
    b = C.BUCKETS
    bucket = (F.when(a < b[0][0], b[0][1]).when(a < b[1][0], b[1][1]).when(a < b[2][0], b[2][1])
              .when(a < b[3][0], b[3][1]).otherwise(b[4][1]))
    buckets = f.filter(F.col("completed") == 1).withColumn("bucket", bucket).groupBy("bucket").count() \
        .withColumnRenamed("count", "flights").toPandas()
    if len(buckets) == 0:
        buckets = pd.DataFrame({"bucket": [], "flights": []})
    return C.finish_tables(_agg(f), _agg(f, "airline"), _agg(f, "origin"), _agg(f, "hour"), _agg(f, "month"),
                           _agg(f, "date"), _agg(f, "dow", "hour"), _agg(f, "route"),
                           _agg(bad, "delay_reason"), buckets)
