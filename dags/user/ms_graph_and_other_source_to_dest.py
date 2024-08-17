import pendulum

from airflow import DAG
from airflow.decorators import task


__version__ = '0.0.1'

with DAG(
    dag_id=f'ms_graph_and_other_source_to_dest',
    schedule=None,
    start_date=pendulum.datetime(),
) as dag:
    @task()
    def load_user_from_source():
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        pg_hook = PostgresHook("pg_source_conn")
        existing_users = pg_hook.run(
            sql="SELECT * FROM employees",
            handler=lambda cursor: cursor.fetchall(),
        )
    pass

if __name__ == '__main__':
    dag.test()