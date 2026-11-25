#!/bin/sh
# Create the FusionAuth database on the shared Postgres. Runs once, on the
# first initialisation of the data volume.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
CREATE USER fusionauth WITH PASSWORD '${FUSIONAUTH_DB_PASSWORD}';
CREATE DATABASE fusionauth OWNER fusionauth;
SQL
