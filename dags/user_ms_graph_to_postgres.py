import json
import pendulum
import logging
from airflow import DAG
from airflow.decorators import task

__version__ = "0.0.1"

with DAG(
    "user_ms_graph_to_postgres",
    schedule=None,
    start_date=pendulum.datetime(2024, 8, 17),
    tags=["experiments"],
) as dag:

    @task()
    def extract_user_from_ms_graph():
        from airflow.providers.http.hooks.http import HttpHook

        token = HttpHook.get_connection("ms_graph_conn").password
        headers = {"Authorization": f"Bearer {token}"}

        ms_graph_hook = HttpHook(method="GET", http_conn_id="ms_graph_conn")
        response = ms_graph_hook.run("users", headers=headers)
        # Parse the response to a JSON serializable format
        response_json = response.json()
        logging.info(f"Users response: {response_json}")
        return response_json

    @task()
    def extract_user_from_postgre():
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        pg_hook = PostgresHook("source_postgres")
        existing_users = pg_hook.run(
            sql="SELECT * FROM employees",
            handler=lambda cursor: cursor.fetchall(),
        )

        logging.info(existing_users)
        return existing_users
    
    @task()
    def transform_user(ms_graph_data, postgre_data):
        # Example transformation: merge two data sources
        # You would adjust this to fit your actual transformation logic
        transformed_data = {
            "users_from_graph": ms_graph_data,
            "existing_users_from_pg": postgre_data
        }
        logging.info(f"Transformed data: {transformed_data}")
        return transformed_data

    @task()
    def load_to_dest(transformed_data):
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        dest_hook = PostgresHook("destination_postgres")
        connection = dest_hook.get_conn()
        cursor = connection.cursor()

        # Example DDL to create a table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_data JSONB
        );
        """
        cursor.execute(create_table_query)

        # Example DML to insert data into the table
        insert_query = "INSERT INTO users (user_data) VALUES (%s)"
        for data in transformed_data["users_from_graph"]:
            cursor.execute(insert_query, [json.dumps(data)])

        connection.commit()
        cursor.close()
        connection.close()
        logging.info("Data loaded into destination Postgres.")
    
    ms_graph_data = extract_user_from_ms_graph()
    postgre_data = extract_user_from_postgre()
    transformed_data = transform_user(ms_graph_data, postgre_data)
    # load_to_dest(transformed_data)



if __name__ == "__main__":
    dag.test()
