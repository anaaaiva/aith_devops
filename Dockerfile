FROM apache/airflow:2.7.1

WORKDIR /opt/airflow

COPY requirements.txt .
COPY ./dags/ /opt/airflow/dags/

RUN pip install --no-cache-dir -r requirements.txt