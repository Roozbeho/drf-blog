#!/bin/sh

echo "Waiting for PostgreSQL to start..."

while ! pg_isready -h db -U ${DB_USER} -d ${DB_NAME}; do
  sleep 1
done

echo "PostgreSQL started!"

echo "Apllying all migrations..."
python manage.py migrate

echo "Createing Roles..."
python manage.py create_role

echo "starting server..."
python manage.py runserver 0.0.0.0:8000