@echo off
set PGPASSWORD=Chaca1986!
REM Ejecuta el script SQL
psql -h localhost -U fr94901 -d forecaist -f ventas-pronostico-app/src/db/forecaist_schema.sql

REM Ejecuta la migración de datos
python ventas-pronostico-app/src/db/migrate_data.py

pause