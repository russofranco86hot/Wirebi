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
XLSX_FILE_PATH = '../data/DB.xlsx'

# --- IDs por defecto (Puedes ajustarlos si ya tienes IDs específicos) ---
DEFAULT_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)

def insert_dim_keyfigures(conn):
    """Inserta las figuras clave si no existen."""
    key_figures_data = [
        (1, 'Sales', 'history', True, 1),
        (2, 'Order', 'forecast', True, 2),
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

def get_key_figure_id_by_name(conn, name):
    """Obtiene el ID de una figura clave por su nombre (string)."""
    with conn.cursor() as cur:
        cur.execute("SELECT key_figure_id FROM dim_keyfigures WHERE name = %s;", (name,))
        result = cur.fetchone()
        return result[0] if result else None

def migrate_db_xlsx_to_postgres(file_path):
    """
    Lee el archivo DB.xlsx e inserta los datos.
    """
    try:
        df = pd.read_excel(file_path)
        print(f"Archivo '{file_path}' leído exitosamente. Primeras 5 filas:")
        print(df.head())

        df.rename(columns={
            'Month': 'period',
            'DPG': 'client_name', # Ahora mapeamos a 'client_name' para la tabla dim_clients
            'SKU': 'sku_name',    # Ahora mapeamos a 'sku_name' para la tabla dim_skus
            'Sum of Quantity': 'value',
            'KeyFigure': 'key_figure_name'
        }, inplace=True)

        df.dropna(subset=['key_figure_name', 'period', 'value', 'client_name', 'sku_name'], inplace=True)
        
        df['period'] = pd.to_datetime(df['period']).dt.date

        with get_db_connection() as conn:
            insert_dim_keyfigures(conn)
            
            sales_kf_id = get_key_figure_id_by_name(conn, 'Sales')
            order_kf_id = get_key_figure_id_by_name(conn, 'Order')

            if sales_kf_id is None:
                print("Error: 'Sales' KeyFigure ID no encontrado en dim_keyfigures. Asegúrate de que exista.")
                return
            if order_kf_id is None:
                print("Error: 'Order' KeyFigure ID no encontrado en dim_keyfigures. Asegúrate de que exista.")
                return

            history_data_to_insert = []
            forecast_versioned_data_to_insert = []
            
            client_name_to_uuid_map = {} # Mapeo de nombre de cliente a UUID
            sku_name_to_uuid_map = {}    # Mapeo de nombre de SKU a UUID

            initial_version_id = uuid.uuid4()
            initial_forecast_run_id = uuid.uuid4()
            
            try:
                with conn.cursor() as cur:
                    # Insertar registros en dim_clients y dim_skus primero
                    # Recorrer todos los nombres de clientes y SKUs únicos en el DataFrame
                    unique_client_names = df['client_name'].unique()
                    for c_name in unique_client_names:
                        c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(c_name))
                        client_name_to_uuid_map[c_name] = c_uuid
                        cur.execute("""
                            INSERT INTO dim_clients (client_id, client_name)
                            VALUES (%s, %s)
                            ON CONFLICT (client_id) DO UPDATE SET client_name = EXCLUDED.client_name;
                        """, (c_uuid, c_name))
                    
                    unique_sku_names = df['sku_name'].unique()
                    for s_name in unique_sku_names:
                        s_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(s_name))
                        sku_name_to_uuid_map[s_name] = s_uuid
                        cur.execute("""
                            INSERT INTO dim_skus (sku_id, sku_name)
                            VALUES (%s, %s)
                            ON CONFLICT (sku_id) DO UPDATE SET sku_name = EXCLUDED.sku_name;
                        """, (s_uuid, s_name))
                    conn.commit()
                    print("Nombres de clientes y SKUs insertados/verificados en tablas dimensionales.")

                    # forecast_smoothing_parameters (usa un client_id genérico para este registro, ahora desde el mapa)
                    # Tomamos el UUID del primer cliente para este registro dummy, o uno fijo si no hay clientes.
                    first_client_uuid_for_forecast = next(iter(client_name_to_uuid_map.values()), uuid.UUID('a1b2c3d4-e5f6-7890-1234-567890abcdef'))
                    cur.execute("""
                        INSERT INTO forecast_smoothing_parameters (forecast_run_id, client_id, alpha, user_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (forecast_run_id) DO NOTHING;
                    """, (initial_forecast_run_id, first_client_uuid_for_forecast, 0.5, DEFAULT_USER_ID))
                    conn.commit()
                    
                    # forecast_versions
                    cur.execute("""
                        INSERT INTO forecast_versions (version_id, client_id, name, created_by, history_source, model_used, forecast_run_id, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (version_id) DO NOTHING;
                    """, (initial_version_id, first_client_uuid_for_forecast, 'Carga Inicial DB.xlsx', DEFAULT_USER_ID, 'sales', 'Carga Excel Original', initial_forecast_run_id, 'Datos cargados del archivo DB.xlsx'))
                    conn.commit()

            except Exception as e:
                print(f"Advertencia: Error al insertar/verificar registros iniciales o dim_clients/skus: {e}. Puede que ya existan.")
                conn.rollback()

            # --- LÓGICA PARA ELIMINAR DUPLICADOS ANTES DE LA INSERCIÓN ---
            df_processed = df.copy() 

            df_sales = df_processed[df_processed['key_figure_name'] == 'Sales']
            df_order = df_processed[df_processed['key_figure_name'] == 'Order']

            base_pk_cols = ['client_name', 'sku_name', 'period'] # Usamos nombres para el drop_duplicates

            if not df_sales.empty:
                initial_sales_rows = len(df_sales)
                df_sales = df_sales.drop_duplicates(subset=base_pk_cols, keep='first')
                if len(df_sales) < initial_sales_rows:
                    print(f"Eliminadas {initial_sales_rows - len(df_sales)} filas duplicadas para 'Sales' (fact_history).")

            if not df_order.empty:
                initial_order_rows = len(df_order)
                df_order = df_order.drop_duplicates(subset=base_pk_cols, keep='first')
                if len(df_order) < initial_order_rows:
                    print(f"Eliminadas {initial_order_rows - len(df_order)} filas duplicadas para 'Order' (fact_forecast_versioned).")
            # ------------------------------------------------------------------

            # Iterar sobre los DataFrames ya sin duplicados
            for _, row in df_sales.iterrows():
                # Obtener UUIDs de los mapas (ya insertados en dim_clients/skus)
                current_client_id = client_name_to_uuid_map.get(str(row['client_name']).strip())
                current_sku_id = sku_name_to_uuid_map.get(str(row['sku_name']).strip())
                
                # Generar client_final_id como antes (combinación de client y sku, para unicidad)
                client_final_combined_id = f"{str(row['client_name']).strip()}-{str(row['sku_name']).strip()}"
                current_client_final_id = uuid.uuid5(uuid.NAMESPACE_DNS, client_final_combined_id)


                if current_client_id and current_sku_id: # Solo insertar si tenemos IDs válidos
                    history_data_to_insert.append((
                        current_client_id,
                        current_sku_id,
                        current_client_final_id,
                        row['period'],
                        'sales',
                        sales_kf_id,
                        row['value'],
                        DEFAULT_USER_ID
                    ))
                else:
                    print(f"Advertencia: No se pudo encontrar Client ID para '{row['client_name']}' o SKU ID para '{row['sku_name']}'. Fila omitida.")


            for _, row in df_order.iterrows():
                # Obtener UUIDs de los mapas
                current_client_id = client_name_to_uuid_map.get(str(row['client_name']).strip())
                current_sku_id = sku_name_to_uuid_map.get(str(row['sku_name']).strip())

                # Generar client_final_id
                client_final_combined_id = f"{str(row['client_name']).strip()}-{str(row['sku_name']).strip()}"
                current_client_final_id = uuid.uuid5(uuid.NAMESPACE_DNS, client_final_combined_id)

                if current_client_id and current_sku_id: # Solo insertar si tenemos IDs válidos
                    forecast_versioned_data_to_insert.append((
                        initial_version_id,
                        current_client_id,
                        current_sku_id,
                        current_client_final_id,
                        row['period'],
                        order_kf_id,
                        row['value']
                    ))
                else:
                    print(f"Advertencia: No se pudo encontrar Client ID para '{row['client_name']}' o SKU ID para '{row['sku_name']}'. Fila omitida.")


            with conn.cursor() as cursor:
                # --- Insertar en fact_history ---
                if history_data_to_insert:
                    history_query = """
                        INSERT INTO fact_history (client_id, sku_id, client_final_id, period, source, key_figure_id, value, user_id)
                        VALUES %s
                        ON CONFLICT (client_id, sku_id, client_final_id, period, key_figure_id) DO UPDATE
                        SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
                    """
                    extras.execute_values(cursor, history_query, history_data_to_insert,
                                         template="(%s, %s, %s, %s, %s, %s, %s, %s)")
                    print(f"Se insertaron/actualizaron {len(history_data_to_insert)} filas en fact_history.")
                else:
                    print("No hay datos de historial para insertar.")

                # --- Insertar en fact_forecast_versioned ---
                if forecast_versioned_data_to_insert:
                    forecast_versioned_query = """
                        INSERT INTO fact_forecast_versioned (version_id, client_id, sku_id, client_final_id, period, key_figure_id, value)
                        VALUES %s
                        ON CONFLICT (version_id, client_id, sku_id, client_final_id, period, key_figure_id) DO UPDATE
                        SET value = EXCLUDED.value;
                    """
                    extras.execute_values(cursor, forecast_versioned_query, forecast_versioned_data_to_insert,
                                         template="(%s, %s, %s, %s, %s, %s, %s)")
                    print(f"Se insertaron/actualizaron {len(forecast_versioned_data_to_insert)} filas en fact_forecast_versioned.")
                else:
                    print("No hay datos de pronóstico versionados para insertar.")

            conn.commit()
            print("Migración de datos desde DB.xlsx a PostgreSQL completada.")

    except FileNotFoundError:
        print(f"Error: El archivo '{file_path}' no fue encontrado. Asegúrate de que 'DB.xlsx' esté en la carpeta '../data/'.")
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