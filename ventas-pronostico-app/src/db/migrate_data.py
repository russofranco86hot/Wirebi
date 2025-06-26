# ventas-pronostico-app/src/db/migrate_data.py - Versión Final (Añadir DimAdjustmentTypes)

import pandas as pd
import psycopg2
from psycopg2 import extras
import os
import uuid

from psycopg2.extensions import register_adapter, AsIs

def add_uuid_adapter():
    def adapt_uuid(uuid_obj):
        return AsIs(f"'{uuid_obj}'")
    register_adapter(uuid.UUID, adapt_uuid)

add_uuid_adapter()

# --- Configuración de la Base de Datos ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "forecaist")
DB_USER = os.getenv("DB_USER", "fr94901")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Chaca1986!")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- Ruta al archivo XLSX ---
XLSX_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'DB.xlsx')
XLSX_FILE_PATH = os.path.abspath(XLSX_FILE_PATH)

# --- IDs por defecto ---
DEFAULT_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)

def insert_dim_keyfigures(conn):
    key_figures_data = [
        (1, 'Sales', 'history', False, 1),        # False: No editable directamente
        (2, 'Order', 'history', False, 2),        # False: No editable directamente
        (3, 'Shipments', 'history', False, 3),    # False: No editable directamente
        (4, 'Pronóstico Estadístico', 'forecast', True, 4), # True: Editable
        (5, 'Historia Limpia', 'history', False, 5), # False: Calculado, no editable
        (6, 'Pronóstico Final', 'forecast', True, 6), # True: Editable
    ]
    try:
        with conn.cursor() as cur:
            for kf_id, name, applies_to, editable, order in key_figures_data:
                cur.execute("""
                    INSERT INTO dim_keyfigures (key_figure_id, name, applies_to, editable, "order")
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (key_figure_id) DO UPDATE SET name = EXCLUDED.name, applies_to = EXCLUDED.applies_to, editable = EXCLUDED.editable, "order" = EXCLUDED."order";
                """, (kf_id, name, applies_to, editable, order))
        conn.commit()
        print("Figuras clave insertadas/verificadas en dim_keyfigures.")
    except Exception as e:
        print(f"Error al insertar en dim_keyfigures: {e}")
        conn.rollback()
        raise

# --- NUEVA FUNCIÓN: Poblar dim_adjustment_types ---
def insert_dim_adjustment_types(conn):
    adjustment_types_data = [
        (1, 'Manual Qty'),
        (2, 'Manual Pct'),
        (3, 'Override'), # Este es el que usaremos para el primer ajuste
        (4, 'Clean by Pct'),
        # Añade aquí cualquier otro tipo de ajuste que necesites según tu documento
    ]
    try:
        with conn.cursor() as cur:
            for adj_id, name in adjustment_types_data:
                cur.execute("""
                    INSERT INTO dim_adjustment_types (adjustment_type_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (adjustment_type_id) DO UPDATE SET name = EXCLUDED.name;
                """, (adj_id, name))
        conn.commit()
        print("Tipos de ajuste insertados/verificados en dim_adjustment_types.")
    except Exception as e:
        print(f"Error al insertar en dim_adjustment_types: {e}")
        conn.rollback()
        raise
# --- FIN NUEVA FUNCIÓN ---

def get_key_figure_id_by_name(conn, name):
    """Obtiene el ID de una figura clave por su nombre (string)."""
    with conn.cursor() as cur:
        cur.execute("SELECT key_figure_id FROM dim_keyfigures WHERE name = %s;", (name,))
        result = cur.fetchone()
        return result[0] if result else None

def migrate_db_xlsx_to_postgres(file_path):
    """
    Lee el archivo DB.xlsx e inserta todos los datos relevantes en fact_history.
    """
    try:
        df = pd.read_excel(file_path)
        print(f"Archivo '{file_path}' leído exitosamente. Primeras 5 filas:")
        print(df.head())

        df.rename(columns={
            'Month': 'period',
            'DPG': 'client_name',
            'SKU': 'sku_name',
            'Sum of Quantity': 'value',
            'KeyFigure': 'key_figure_name'
        }, inplace=True)

        df.dropna(subset=['key_figure_name', 'period', 'value', 'client_name', 'sku_name'], inplace=True)
        
        df['period'] = pd.to_datetime(df['period']).dt.date

        with get_db_connection() as conn:
            insert_dim_keyfigures(conn)
            insert_dim_adjustment_types(conn) # ¡LLAMADA A LA NUEVA FUNCIÓN!
            
            sales_kf_id = get_key_figure_id_by_name(conn, 'Sales')
            order_kf_id = get_key_figure_id_by_name(conn, 'Order')
            shipments_kf_id = get_key_figure_id_by_name(conn, 'Shipments')
            
            if sales_kf_id is None:
                print("Error: 'Sales' KeyFigure ID no encontrado en dim_keyfigures. Asegúrate de que exista.")
                return
            if order_kf_id is None:
                print("Error: 'Order' KeyFigure ID no encontrado en dim_keyfigures. Asegúrate de que exista.")
                return
            if shipments_kf_id is None:
                print("Error: 'Shipments' KeyFigure ID no encontrado en dim_keyfigures. Asegúrate de que exista.")
                return

            history_data_to_insert = []
            
            client_name_to_uuid_map = {}
            sku_name_to_uuid_map = {}
            
            try:
                with conn.cursor() as cur:
                    unique_client_names = df['client_name'].unique()
                    for c_name in unique_client_names:
                        c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(c_name).strip())
                        client_name_to_uuid_map[c_name] = c_uuid
                        cur.execute("""
                            INSERT INTO dim_clients (client_id, client_name)
                            VALUES (%s, %s)
                            ON CONFLICT (client_id) DO UPDATE SET client_name = EXCLUDED.client_name;
                        """, (c_uuid, c_name.strip()))
                    
                    unique_sku_names = df['sku_name'].unique()
                    for s_name in unique_sku_names:
                        s_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(s_name).strip())
                        sku_name_to_uuid_map[s_name] = s_uuid
                        cur.execute("""
                            INSERT INTO dim_skus (sku_id, sku_name)
                            VALUES (%s, %s)
                            ON CONFLICT (sku_id) DO UPDATE SET sku_name = EXCLUDED.sku_name;
                        """, (s_uuid, s_name.strip()))
                    conn.commit()
                    print("Nombres de clientes y SKUs insertados/verificados en tablas dimensionales.")

                    initial_forecast_run_id = uuid.uuid4()
                    initial_version_id = uuid.uuid4()
                    
                    dummy_client_id_for_forecast = next(iter(client_name_to_uuid_map.values()), uuid.UUID('a1b2c3d4-e5f6-7890-1234-567890abcdef'))
                    
                    cur.execute("""
                        INSERT INTO forecast_smoothing_parameters (forecast_run_id, client_id, alpha, user_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (forecast_run_id) DO NOTHING;
                    """, (initial_forecast_run_id, dummy_client_id_for_forecast, 0.5, DEFAULT_USER_ID))
                    conn.commit()
                    
                    cur.execute("""
                        INSERT INTO forecast_versions (version_id, client_id, name, created_at, created_by, history_source, model_used, forecast_run_id, notes)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
                        ON CONFLICT (version_id) DO NOTHING;
                    """, (initial_version_id, dummy_client_id_for_forecast, 'Initial Excel Load Version', DEFAULT_USER_ID, 'sales', 'Manual Excel Load', initial_forecast_run_id, 'Version created during initial data migration from DB.xlsx'))
                    conn.commit()

            except Exception as e:
                print(f"Advertencia: Error al insertar/verificar registros iniciales para tablas auxiliares o dim_clients/skus: {e}. Puede que ya existan o haya un problema de FK.")
                conn.rollback()

            # --- Lógica para eliminar duplicados antes de la inserción en fact_history ---
            df_processed = df.copy()
            
            history_pk_cols = ['client_name', 'sku_name', 'period', 'key_figure_name']
            
            initial_rows = len(df_processed)
            df_processed = df_processed.drop_duplicates(subset=history_pk_cols, keep='first')
            if len(df_processed) < initial_rows:
                print(f"Eliminadas {initial_rows - len(df_processed)} filas duplicadas para fact_history.")
            # -----------------------------------------------------------------------------

            for _, row in df_processed.iterrows():
                client_name = str(row['client_name']).strip()
                sku_name = str(row['sku_name']).strip()
                key_figure_name = str(row['key_figure_name']).strip()
                value = row['value']

                current_client_id = client_name_to_uuid_map.get(client_name)
                current_sku_id = sku_name_to_uuid_map.get(sku_name)
                
                client_final_combined_id = f"{client_name}-{sku_name}"
                current_client_final_id = uuid.uuid5(uuid.NAMESPACE_DNS, client_final_combined_id)

                kf_id_to_use = None
                source_to_use = None

                if key_figure_name == 'Sales':
                    kf_id_to_use = sales_kf_id
                    source_to_use = 'sales'
                elif key_figure_name == 'Order':
                    kf_id_to_use = order_kf_id
                    source_to_use = 'order'
                elif key_figure_name == 'Shipments':
                    kf_id_to_use = shipments_kf_id
                    source_to_use = 'shipments'
                else:
                    print(f"Advertencia: KeyFigure '{key_figure_name}' no reconocida. Fila omitida.")
                    continue

                if current_client_id and current_sku_id and kf_id_to_use and source_to_use:
                    history_data_to_insert.append((
                        current_client_id,
                        current_sku_id,
                        current_client_final_id,
                        row['period'],
                        source_to_use,
                        kf_id_to_use,
                        value,
                        DEFAULT_USER_ID
                    ))
                else:
                    print(f"Advertencia: Faltan IDs de cliente/SKU o KeyFigure/Source para la fila. Fila omitida.")
            
            with conn.cursor() as cursor:
                if history_data_to_insert:
                    history_query = """
                        INSERT INTO fact_history (client_id, sku_id, client_final_id, period, source, key_figure_id, value, user_id)
                        VALUES %s
                        ON CONFLICT (client_id, sku_id, client_final_id, period, key_figure_id, source) DO UPDATE
                        SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
                    """
                    extras.execute_values(cursor, history_query, history_data_to_insert,
                                         template="(%s, %s, %s, %s, %s, %s, %s, %s)")
                    print(f"Se insertaron/actualizaron {len(history_data_to_insert)} filas en fact_history.")
                else:
                    print("No hay datos de historial para insertar.")
            
            conn.commit()
            print("Migración de datos desde DB.xlsx a PostgreSQL completada.")

    except FileNotFoundError:
        print(f"Error: El archivo '{file_path}' no fue encontrado. Asegúrate de que '{XLSX_FILE_PATH}' exista en la estructura.")
    except KeyError as e:
        print(f"Error: Columna faltante en el archivo XLSX o nombre incorrecto: {e}. Revisa tus nombres de columnas en 'DB.xlsx' y el mapeo en el script.")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la migración: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()

if __name__ == "__main__":
    print("Iniciando migración de datos desde DB.xlsx con mapeo por nombre de KeyFigure...")
    migrate_db_xlsx_to_postgres(XLSX_FILE_PATH)
    print("Proceso de migración finalizado.")