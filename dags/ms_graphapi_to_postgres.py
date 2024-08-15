from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from datetime import datetime, timedelta
import requests
import json

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 8, 16),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'ms_graphapi_to_postgres',
    default_args=default_args,
    description='A DAG to integrate MS GraphAPI and PostgreSQL and load data into a new PostgreSQL DB',
    schedule_interval=timedelta(days=1),
)

# Extract data from MS Graph API
def extract_from_ms_graph_api(**kwargs):
    # Securely access the token from Airflow Variables
    token = Variable.get("MS_GRAPH_API_TOKEN")
    headers = {'Authorization': f'Bearer {token}'}
    
    # Example API call (replace with actual Graph API endpoint)
    url = "https://graph.microsoft.com/v1.0/users"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        users = response.json()
        return users
    else:
        raise Exception(f"Failed to fetch data from MS Graph API: {response.text}")

# Extract data from PostgreSQL
def extract_from_postgres(**kwargs):
    source_pg_hook = PostgresHook(postgres_conn_id='source_postgres')
    connection = source_pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM employees;")
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return data

# Transform the data (optional)
def transform_data(ms_graph_data, postgres_data, **kwargs):
    combined_data = []

    for user in ms_graph_data['value']:
        for employee in postgres_data:
            if user['userPrincipalName'] == employee[0]:  # Match on Username
                combined_entry = {
                    'username': user['userPrincipalName'],
                    'full_name': user['displayName'],
                    'email': user['mail'],
                    'department': employee[5],  # Example: department from PostgreSQL
                }
                combined_data.append(combined_entry)
    
    return combined_data

# Load data into the new PostgreSQL database
def load_into_new_postgres(combined_data, **kwargs):
    dest_pg_hook = PostgresHook(postgres_conn_id='destination_postgres')
    connection = dest_pg_hook.get_conn()
    cursor = connection.cursor()

    for entry in combined_data:
        cursor.execute("""
            INSERT INTO new_employees (username, full_name, email, department)
            VALUES (%s, %s, %s, %s);
        """, (entry['username'], entry['full_name'], entry['email'], entry['department']))
    
    connection.commit()
    cursor.close()
    connection.close()

# Define tasks
extract_ms_graph_task = PythonOperator(
    task_id='extract_from_ms_graph_api',
    python_callable=extract_from_ms_graph_api,
    provide_context=True,
    dag=dag,
)

extract_postgres_task = PythonOperator(
    task_id='extract_from_postgres',
    python_callable=extract_from_postgres,
    provide_context=True,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    op_kwargs={
        'ms_graph_data': "{{ ti.xcom_pull(task_ids='extract_from_ms_graph_api') }}",
        'postgres_data': "{{ ti.xcom_pull(task_ids='extract_from_postgres') }}"
    },
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_into_new_postgres',
    python_callable=load_into_new_postgres,
    provide_context=True,
    op_kwargs={'combined_data': "{{ ti.xcom_pull(task_ids='transform_data') }}"},
    dag=dag,
)

# Define the order of tasks
[extract_ms_graph_task, extract_postgres_task] >> transform_task >> load_task
