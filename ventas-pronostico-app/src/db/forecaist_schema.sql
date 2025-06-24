-- Database: forecaist

-- DROP DATABASE IF EXISTS forecaist;

/*CREATE DATABASE forecaist
    WITH
    OWNER = fr94901
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Argentina.1252'
    LC_CTYPE = 'Spanish_Argentina.1252'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;
*/

DROP SCHEMA public CASCADE; -- Eliminar todo en el esquema público
CREATE SCHEMA public;      -- Crear un esquema público nuevo
GRANT ALL PRIVILEGES ON SCHEMA public TO fr94901; -- Dar permisos a tu usuario en el nuevo esquema
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO fr94901; -- Permisos para futuras tablas

-- Asegurarse de que el usuario tenga permisos en el esquema public
GRANT ALL PRIVILEGES ON SCHEMA public TO fr94901;

-- Si ya hay tablas, otórgale permisos sobre ellas también
-- (Opcional, si estás recreando todo desde cero, el comando de abajo ya lo cubre)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fr94901;

-- Otorga permisos para futuras tablas que se creen en el esquema
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO fr94901;

-- Salir de psql
GRANT ALL ON SCHEMA public TO fr94901;

GRANT TEMPORARY, CONNECT ON DATABASE forecaist TO PUBLIC;

GRANT ALL ON DATABASE forecaist TO fr94901;

-- Da permisos de uso sobre el esquema (necesario para ver objetos)
GRANT USAGE ON SCHEMA public TO fr94901;
-- Da permisos sobre todas las tablas actuales del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fr94901;
-- Da permisos sobre todas las secuencias (para columnas SERIAL/IDENTITY)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fr94901;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fr94901;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO fr94901;

-- DIMENSIONAL TABLES

-- Existing Dimensional Tables (as you have them)
CREATE TABLE IF NOT EXISTS dim_keyfigures (
    key_figure_id INT PRIMARY KEY,
    name TEXT NOT NULL,
    applies_to TEXT CHECK (applies_to IN ('history', 'forecast')),
    editable BOOLEAN DEFAULT TRUE,
    "order" INT
);

CREATE TABLE IF NOT EXISTS dim_adjustment_types (
    adjustment_type_id INT PRIMARY KEY,
    name TEXT NOT NULL
);

-- NEW Dimensional Tables for Clients and SKUs
CREATE TABLE IF NOT EXISTS dim_clients (
    client_id UUID PRIMARY KEY,
    client_name TEXT NOT NULL UNIQUE, -- El nombre descriptivo del cliente
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_skus (
    sku_id UUID PRIMARY KEY,
    sku_name TEXT NOT NULL UNIQUE, -- El nombre descriptivo del SKU
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Auxiliary Tables (as you have them)
CREATE TABLE IF NOT EXISTS forecast_smoothing_parameters (
    forecast_run_id UUID PRIMARY KEY,
    client_id UUID NOT NULL,
    alpha FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id UUID,
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id) -- New FK
);

CREATE TABLE IF NOT EXISTS forecast_versions (
    version_id UUID PRIMARY KEY,
    client_id UUID NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    history_source TEXT CHECK (history_source IN ('shipments', 'sales')),
    model_used TEXT,
    forecast_run_id UUID,
    notes TEXT,
    FOREIGN KEY (forecast_run_id) REFERENCES forecast_smoothing_parameters(forecast_run_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id) -- New FK
);

-- Fact Tables (Update FOREIGN KEY constraints)

CREATE TABLE IF NOT EXISTS fact_history (
    client_id UUID NOT NULL,
    sku_id UUID NOT NULL,
    client_final_id UUID NOT NULL,
    period DATE NOT NULL,
    source TEXT CHECK (source IN ('shipments', 'sales')),
    key_figure_id INT NOT NULL,
    value FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    user_id UUID,
    PRIMARY KEY (client_id, sku_id, client_final_id, period, key_figure_id),
    FOREIGN KEY (key_figure_id) REFERENCES dim_keyfigures(key_figure_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id),
    FOREIGN KEY (sku_id) REFERENCES dim_skus(sku_id),
    UNIQUE (client_id, sku_id, client_final_id, period, key_figure_id, source)
);

CREATE TABLE IF NOT EXISTS fact_forecast_stat (
    client_id UUID NOT NULL,
    sku_id UUID NOT NULL,
    client_final_id UUID NOT NULL,
    period DATE NOT NULL,
    value FLOAT,
    model_used TEXT,
    forecast_run_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id UUID,
    PRIMARY KEY (client_id, sku_id, client_final_id, period),
    FOREIGN KEY (forecast_run_id) REFERENCES forecast_smoothing_parameters(forecast_run_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id), -- New FK
    FOREIGN KEY (sku_id) REFERENCES dim_skus(sku_id) -- New FK
);

CREATE TABLE IF NOT EXISTS fact_adjustments (
    client_id UUID NOT NULL,
    sku_id UUID NOT NULL,
    client_final_id UUID NOT NULL,
    period DATE NOT NULL,
    key_figure_id INT NOT NULL,
    adjustment_type_id INT NOT NULL,
    value FLOAT,
    comment TEXT,
    user_id UUID,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (client_id, sku_id, client_final_id, period, key_figure_id),
    FOREIGN KEY (key_figure_id) REFERENCES dim_keyfigures(key_figure_id),
    FOREIGN KEY (adjustment_type_id) REFERENCES dim_adjustment_types(adjustment_type_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id), -- New FK
    FOREIGN KEY (sku_id) REFERENCES dim_skus(sku_id) -- New FK
);

CREATE TABLE IF NOT EXISTS fact_forecast_versioned (
    version_id UUID NOT NULL,
    client_id UUID NOT NULL,
    sku_id UUID NOT NULL,
    client_final_id UUID NOT NULL,
    period DATE NOT NULL,
    key_figure_id INT NOT NULL,
    value FLOAT,
    PRIMARY KEY (version_id, client_id, sku_id, client_final_id, period, key_figure_id),
    FOREIGN KEY (version_id) REFERENCES forecast_versions(version_id),
    FOREIGN KEY (key_figure_id) REFERENCES dim_keyfigures(key_figure_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id), -- New FK
    FOREIGN KEY (sku_id) REFERENCES dim_skus(sku_id) -- New FK
);

CREATE TABLE IF NOT EXISTS manual_input_comments (
    client_id UUID NOT NULL,
    sku_id UUID NOT NULL,
    client_final_id UUID NOT NULL,
    period DATE NOT NULL,
    key_figure_id INT NOT NULL,
    comment TEXT,
    user_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (client_id, sku_id, client_final_id, period, key_figure_id),
    FOREIGN KEY (key_figure_id) REFERENCES dim_keyfigures(key_figure_id),
    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id), -- New FK
    FOREIGN KEY (sku_id) REFERENCES dim_skus(sku_id) -- New FK
);

