from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="weather_forecast_spark",
    default_args=default_args,
    description="Прогноз погоды: PySpark",
    schedule_interval="0 8 * * *",
    start_date=datetime(2024, 4, 20),
    catchup=False,
    tags=["weather", "spark", "ml", "features"],
) as dag:
    spark_job = SparkSubmitOperator(
        task_id="weather_forecast_spark",  # имя любое
        application="/opt/airflow/spark/weather_forecast_spark.py",  # путь до скрипта, который надо прогнать
        name="weather_forecast_spark",  # имя любое
        conn_id="spark_local",  # должно совпадать с именем, заданным через админку при создании подключения
        dag=dag,
    )
spark_job
