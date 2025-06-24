# PLSQL debe ser agregado en el PATH de las variables de entorno del sistema operativo.

# Este archivo debe ser invocado:
# Abre una terminal y conéctate a psql como superusuario (postgres). Desde la RAÍZ de Wirebi
psql -h localhost -U fr94901 -d forecaist -f ventas-pronostico-app/src/db/forecaist_schema.sql

# luego, migrar la data

# Desde la RAÍZ de Wirebi
python ventas-pronostico-app/src/db/migrate_data.py