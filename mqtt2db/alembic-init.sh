#!/bin/bash

SQL_DB=$(echo $SQL_SERVER | awk -F'/' '{print $NF}')

mariadb -uroot -p -e "CREATE DATABASE $SQL_DB"
alembic init alembic

# edit alembic.init-sqlalchemy.url and target_metadata
source .env
sed -i "s/sqlalchemy.url = .*/sqlalchemy.url = $SQL_SERVER/g" alembic.ini
sed -i "s/target_metadata = .*/target_metadata = Base.metadata/g" alembic/env.py
sed -i "1i from db_models import Base" alembic/env.py

alembic revision --autogenerate -m "init"
alembic upgrade head
