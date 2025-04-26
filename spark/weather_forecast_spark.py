import logging
from datetime import datetime, timedelta

import requests
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag
from pyspark.sql.window import Window
from sklearn.metrics import mean_absolute_error, mean_squared_error


def run_weather_pipeline_spark():
    spark = SparkSession.builder.appName("WeatherForecast").master("spark://spark-master:7077").getOrCreate()
    spark.sparkContext.setLogLevel("INFO")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    today = datetime.today()
    start_date = (today - timedelta(days=1015)).strftime("%Y-%m-%d")
    end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 59.93,
        "longitude": 30.31,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Moscow",
    }

    response = requests.get(url, params=params)
    data = response.json()
    if "daily" not in data:
        raise ValueError("❌ Нет данных от API")

    rows = list(
        zip(
            data["daily"]["time"],
            data["daily"]["temperature_2m_min"],
            data["daily"]["temperature_2m_max"],
        )
    )
    df = spark.createDataFrame(rows, ["date", "t_min", "t_max"])
    df = df.withColumn("date", col("date").cast("date"))

    df = df.orderBy("date")

    N = 7
    w = Window.orderBy("date")

    for i in range(1, N + 1):
        df = df.withColumn(f"t_min_lag_{i}", lag("t_min", i).over(w))
        df = df.withColumn(f"t_max_lag_{i}", lag("t_max", i).over(w))
    df = df.dropna()

    total_count = df.count()
    train_count = int(total_count * 0.8)

    train_df = df.limit(train_count)
    test_df = df.subtract(train_df)

    feature_cols = [f"t_min_lag_{i}" for i in range(1, N + 1)] + [f"t_max_lag_{i}" for i in range(1, N + 1)]

    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
    train_prepared = assembler.transform(train_df)
    test_prepared = assembler.transform(test_df)

    lr = LinearRegression(featuresCol="features", labelCol="t_max")
    model = lr.fit(train_prepared)

    predictions = model.transform(test_prepared)

    preds = predictions.select("t_max", "prediction").collect()

    y_true = [x["t_max"] for x in preds]
    y_pred = [x["prediction"] for x in preds]

    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)

    print("📈 Метрики логистической регрессии на PySpark:")
    print(f"  MAE: {mae:.2f}")
    print(f"  MSE: {mse:.2f}")
    print("🔍 Пример:")
    print(f"  True: {y_true[0]:.2f}°C")
    print(f"  Pred: {y_pred[0]:.2f}°C")

    spark.stop()


run_weather_pipeline_spark()
