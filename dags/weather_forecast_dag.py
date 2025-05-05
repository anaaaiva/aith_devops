from datetime import datetime, timedelta

import pandas as pd
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from sklearn.metrics import mean_absolute_error, mean_squared_error


def run_weather_pipeline():
    # Получаем данные за последние 10 дней
    today = datetime.today()
    start_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
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
        raise ValueError("No weather data returned from API")

    df = pd.DataFrame(data["daily"])
    df["date"] = pd.to_datetime(df["time"])

    # Прогноз на завтра — среднее значение за последние 3 дня
    forecast = df[["temperature_2m_max", "temperature_2m_min"]].tail(3).mean()
    y_pred = [forecast["temperature_2m_max"], forecast["temperature_2m_min"]]

    # Истинные данные - берём последний день
    y_true = [df.iloc[-1]["temperature_2m_max"], df.iloc[-1]["temperature_2m_min"]]

    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)

    print("📅 Прогноз на завтра:")
    print(f"  Max temp: {y_pred[0]:.2f}°C")
    print(f"  Min temp: {y_pred[1]:.2f}°C")
    print("📊 Метрики прогноза (по последнему дню как реальному):")
    print(f"  MAE: {mae:.2f}")
    print(f"  MSE: {mse:.2f}")


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="weather_forecast_dag",
    default_args=default_args,
    description="Прогноз погоды в СПб с метриками",
    schedule_interval="0 8 * * *",  # каждый день в 08:00
    start_date=datetime(2024, 4, 20),
    catchup=False,
    tags=["weather", "forecast"],
) as dag:
    run_pipeline = PythonOperator(
        task_id="run_weather_forecast",
        python_callable=run_weather_pipeline,
    )

run_pipeline
