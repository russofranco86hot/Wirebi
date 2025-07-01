# ventas-pronostico-app/src/db/migrate_data.py - Versión Final (Añadir DimAdjustmentTypes)

import pandas as pd
import psycopg2
from psycopg2 import extras
import os
import uuid
import sys 

current_dir = os.path.dirname(os.path.abspath(__file__))

from psycopg2.extensions import register_adapter, AsIs

def add_uuid_adapter():
    def adapt_uuid(uuid_obj):
        return extras.AsIs(f"'{uuid_obj}'") 
    psycopg2.extensions.register_adapter(uuid.UUID, adapt_uuid) 

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

# --- Ajustar sys.path para encontrar el módulo 'app' ---
backend_parent_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..', 'backend'))
if backend_parent_dir not in sys.path:
    sys.path.insert(0, backend_parent_dir)

from app import models, schemas
from app.database import SessionLocal, engine


def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)

def create_tables():
    """Crea o actualiza las tablas de la base de datos."""
    models.Base.metadata.create_all(bind=engine)
    print("Tablas de la base de datos creadas/actualizadas.")

def insert_dim_keyfigures(conn):
    # ¡LISTA MAESTRA DE 8 KEY FIGURES!
    key_figures_data = [
        (schemas.KEY_FIGURE_SALES_ID, 'Sales', 'history', False, 1), 
        (schemas.KEY_FIGURE_SMOOTHED_SALES_ID, 'Smoothed Sales', 'history', False, 2), 
        (schemas.KEY_FIGURE_ORDERS_ID, 'Orders', 'history', False, 3), 
        (schemas.KEY_FIGURE_SMOOTHED_ORDERS_ID, 'Smoothed Orders', 'history', False, 4), 
        (schemas.KEY_FIGURE_MANUAL_INPUT_ID, 'Manual input', 'history', True, 5), 
        (schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID, 'Statistical forecast Sales', 'forecast', False, 6), 
        (schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID, 'Statistical forecast Orders', 'forecast', False, 7), 
        (schemas.KEY_FIGURE_FINAL_FORECAST_ID, 'Final Forecast', 'forecast', True, 8), 
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

def insert_dim_adjustment_types(conn):
    adjustment_types_data = [
        (1, 'Cantidad'),
        (2, 'Porcentaje'),
        (3, 'Override'), 
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
            'KeyFigure': 'key_figure_name' # Contendrá 'Sales', 'Order', 'Shipments'
        }, inplace=True)

        df.dropna(subset=['key_figure_name', 'period', 'value', 'client_name', 'sku_name'], inplace=True)
        
        df['period'] = pd.to_datetime(df['period']).dt.date

        with get_db_connection() as conn:
            insert_dim_keyfigures(conn)
            insert_dim_adjustment_types(conn)
            
            # Obtener los IDs de las nuevas Key Figures por nombre
            sales_kf_id = get_key_figure_id_by_name(conn, 'Sales') 
            orders_kf_id = get_key_figure_id_by_name(conn, 'Orders')
            manual_input_kf_id = get_key_figure_id_by_name(conn, 'Manual input')
            
            if sales_kf_id is None:
                print("Error: 'Sales' KeyFigure ID no encontrado. No se puede migrar fact_history.")
                return
            if orders_kf_id is None:
                print("Error: 'Orders' KeyFigure ID no encontrado. No se puede migrar fact_history.")
                return
            if manual_input_kf_id is None:
                print("Error: 'Manual input' KeyFigure ID no encontrado. No se puede migrar fact_history.")
                return


            history_data_to_insert_dicts = {} 
            manual_input_data_to_insert_dicts = {} # Datos para 'Manual input' (ID 5)
            
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

            df_processed = df.copy()
            
            df_processed = df_processed[df_processed['key_figure_name'].isin(['Sales', 'Order', 'Shipments'])].copy()

            for _, row in df_processed.iterrows():
                client_name = str(row['client_name']).strip()
                sku_name = str(row['sku_name']).strip()
                key_figure_name_from_excel = str(row['key_figure_name']).strip() # 'Sales', 'Order', 'Shipments'
                value = row['value']

                current_client_id = client_name_to_uuid_map.get(client_name)
                current_sku_id = sku_name_to_uuid_map.get(sku_name)
                
                client_final_combined_id = f"{client_name}-{sku_name}"
                current_client_final_id = uuid.uuid5(uuid.NAMESPACE_DNS, client_final_combined_id)

                kf_id_for_raw_history = None
                source_for_raw_history = key_figure_name_from_excel.lower() # 'sales', 'order', 'shipments'

                if key_figure_name_from_excel == 'Sales':
                    kf_id_for_raw_history = sales_kf_id
                elif key_figure_name_from_excel == 'Order' or key_figure_name_from_excel == 'Shipments':
                    kf_id_for_raw_history = orders_kf_id # Mapeamos 'Order' y 'Shipments' a la KF 'Orders'
                
                if current_client_id and current_sku_id and kf_id_for_raw_history and source_for_raw_history and pd.notna(value):
                    pk_tuple_raw_history = (current_client_id, current_sku_id, current_client_final_id, row['period'], kf_id_for_raw_history, source_for_raw_history)
                    history_data_to_insert_dicts[pk_tuple_raw_history] = (
                        current_client_id, current_sku_id, current_client_final_id, row['period'],
                        source_for_raw_history, kf_id_for_raw_history, value, DEFAULT_USER_ID
                    )
                    
                    if pd.notna(value): 
                         pk_tuple_manual_input = (current_client_id, current_sku_id, current_client_final_id, row['period'], manual_input_kf_id, 'sales') # La fuente para Manual input
                         manual_input_data_to_insert_dicts[pk_tuple_manual_input] = (
                            current_client_id, current_sku_id, current_client_final_id, row['period'],
                            'sales', manual_input_kf_id, value, 
                            DEFAULT_USER_ID
                        )
                else:
                    print(f"Advertencia: Faltan IDs o valores nulos para la fila ({client_name}, {sku_name}, {row['period']}, {key_figure_name_from_excel}, {value}). Fila omitida.")
            
            # Convertir diccionarios a listas de tuplas para execute_values
            history_data_to_insert_final = list(history_data_to_insert_dicts.values())
            manual_input_data_to_insert_final = list(manual_input_data_to_insert_dicts.values())


            if len(history_data_to_insert_final) < len(history_data_to_insert_dicts): 
                print(f"Eliminadas {len(history_data_to_insert_dicts) - len(history_data_to_insert_final)} filas duplicadas internas para Historial Crudo.")
            if len(manual_input_data_to_insert_final) < len(manual_input_data_to_insert_dicts): 
                print(f"Eliminadas {len(manual_input_data_to_insert_dicts) - len(manual_input_data_to_insert_final)} filas duplicadas internas para Manual input.")
            
            with conn.cursor() as cursor:
                # Query para Historial Crudo y Manual Input (ambos van a fact_history)
                history_query = """
                    INSERT INTO fact_history (client_id, sku_id, client_final_id, period, source, key_figure_id, value, user_id)
                    VALUES %s
                    ON CONFLICT (client_id, sku_id, client_final_id, period, key_figure_id, source) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
                """
                if history_data_to_insert_final:
                    extras.execute_values(cursor, history_query, history_data_to_insert_final,
                                            template="(%s, %s, %s, %s, %s, %s, %s, %s)")
                    print(f"Se insertaron/actualizaron {len(history_data_to_insert_final)} filas de Historial Crudo en fact_history.")
                else:
                    print("No hay datos de historial crudo para insertar.")
                
                if manual_input_data_to_insert_final: 
                    extras.execute_values(cursor, history_query, manual_input_data_to_insert_final, 
                                            template="(%s, %s, %s, %s, %s, %s, %s, %s)")
                    print(f"Se insertaron/actualizaron {len(manual_input_data_to_insert_final)} filas de Manual input en fact_history.")
                else:
                    print("No hay datos de Manual input para insertar.")

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
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Eliminar datos de fact_history y fact_forecast_stat antes de la migración.
            # Esto es CRÍTICO cuando se cambian IDs o la estructura de la PK.
            print("Eliminando datos existentes de fact_history y fact_forecast_stat...")
            cur.execute("DELETE FROM fact_history;")
            cur.execute("DELETE FROM fact_forecast_stat;") # <-- Asegurar que se limpia esta tabla
            conn.commit()
            print("Datos existentes en fact_history y fact_forecast_stat eliminados.")
    
    migrate_db_xlsx_to_postgres(XLSX_FILE_PATH)
    print("Proceso de migración finalizado.")