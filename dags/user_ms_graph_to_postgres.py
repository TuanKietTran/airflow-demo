import pendulum

from airflow import DAG
from airflow.decorators import task

__version__ = "0.0.1"

with DAG(
    "user_ms_graph_to_postgres",
    schedule=None,
    start_date=pendulum.datetime(2024, 8, 16),
    tags=["experiments"],
) as dag:

    @task()
    def extract_user_from_ms_graph_to_pg():
        from airflow.providers.http.hooks.http import HttpHook
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        token = HttpHook.get_connection("ms_graph_conn").password
        headers = {"Authorization": f"Bearer {token}"}

        ms_graph_hook = HttpHook(method="GET", http_conn_id="ms_graph_conn")
        user_response = ms_graph_hook.run("users", headers=headers)
        print(user_response.json())

        pg_hook = PostgresHook("pg_conn")
        existing_users = pg_hook.run(
            sql="SELECT * FROM employees",
            handler=lambda cursor: cursor.fetchall(),
        )

    extract_user_from_ms_graph_to_pg()


if __name__ == "__main__":
    dag.test()
