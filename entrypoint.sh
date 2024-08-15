#!/bin/bash

# If in remote mode, clone the DAGs repository
if [ "$DAG_SOURCE" = "remote" ]; then
    git clone $GIT_REPO_URL /usr/local/airflow/dags
fi

# Start the Airflow service (webserver or scheduler)
exec airflow "$@"
