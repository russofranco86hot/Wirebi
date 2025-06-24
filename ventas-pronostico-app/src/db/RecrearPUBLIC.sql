--Abre una terminal y conéctate a psql como superusuario (postgres). 
-- Ejecuta lo siguiente (reemplaza fr94901 con tu usuario de DB):

\c forecaist; -- Conectarse a tu base de datos
DROP SCHEMA public CASCADE; -- Eliminar todo en el esquema público
CREATE SCHEMA public;      -- Crear un esquema público nuevo
GRANT ALL PRIVILEGES ON SCHEMA public TO fr94901; -- Dar permisos a tu usuario en el nuevo esquema
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO fr94901; -- Permisos para futuras tablas
\q -- Salir de psql

-- PLSQL debe ser agregado en el PATH de las variables de entorno del sistema operativo.

-- # Desde la RAÍZ de Wirebi
-- psql -h localhost -U fr94901 -d forecaist -f ventas-pronostico-app/src/db/forecaist_schema.sql

-- luego, migrar la data

-- # Desde la RAÍZ de Wirebi
-- python ventas-pronostico-app/src/db/migrate_data.py