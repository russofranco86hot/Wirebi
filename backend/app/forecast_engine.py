# backend/app/forecast_engine.py - Versión con Historia Suavizada

import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import ETS, ARIMA 
from sqlalchemy.orm import Session
from datetime import date, timedelta
import uuid
import logging

from . import models, crud, schemas 
from psycopg2 import extras 

logger = logging.getLogger(__name__)

# --- Definir DEFAULT_USER_ID aquí para que sea accesible en este módulo ---
DEFAULT_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000001') 
# -------------------------------------------------------------------------

# --- Modelos de Forecast que Forecaist puede usar ---
FORECAST_MODELS = {
    "ETS": ETS,
    "ARIMA": ARIMA,
}

# --- Constante para el número mínimo de puntos de datos para el pronóstico ---
MIN_FORECAST_POINTS = 5 

def calculate_smoothed_history(data_df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """
    Calcula la historia suavizada utilizando suavizado exponencial simple.
    Requiere un DataFrame con 'ds' (fechas) y 'y' (valores).
    """
    if data_df.empty:
        return pd.DataFrame(columns=['ds', 'y_smoothed'])

    # Ordenar por fecha para asegurar que el suavizado sea secuencial
    data_df = data_df.sort_values(by='ds').reset_index(drop=True)

    smoothed_values = []
    # Inicializar el primer valor suavizado con el primer valor crudo
    if not data_df.empty:
        smoothed_values.append(data_df.iloc[0]['y'])
    else:
        return pd.DataFrame(columns=['ds', 'y_smoothed'])

    for i in range(1, len(data_df)):
        # Formula de suavizado exponencial simple: S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
        next_smoothed_value = alpha * data_df.iloc[i]['y'] + (1 - alpha) * smoothed_values[-1]
        smoothed_values.append(next_smoothed_value)
    
    # Crear un DataFrame con los resultados suavizados
    smoothed_df = pd.DataFrame({
        'ds': data_df['ds'],
        'y_smoothed': smoothed_values
    })
    return smoothed_df


def generate_forecast(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    history_source: str, # 'sales' o 'shipments'
    smoothing_alpha: float, # Parámetro alpha para suavizado (si se usa)
    model_name: str, # "ETS", "ARIMA", etc.
    forecast_horizon: int = 12 # Cuántos períodos hacia adelante pronosticar
):
    """
    Genera un pronóstico para un SKU-Cliente dado, usando su historia,
    y guarda la historia suavizada y el pronóstico.
    """
    logger.info(f"Iniciando generación de forecast para Client: {client_id}, SKU: {sku_id}")

    history_kf_id_to_fetch = None
    if history_source == 'sales':
        history_kf_id_to_fetch = 1 
    elif history_source == 'order':
        history_kf_id_to_fetch = 2
    else:
        raise ValueError(f"Fuente histórica '{history_source}' no reconocida para obtener Key Figure ID.")

    # 1. Obtener la historia cruda desde fact_history
    historical_data_raw = crud.get_fact_history_data(
        db=db,
        client_ids=[client_id],
        sku_ids=[sku_id],
        sources=[history_source],
        key_figure_ids=[history_kf_id_to_fetch], 
        limit=99999
    )

    if not historical_data_raw:
        logger.warning(f"No hay datos históricos disponibles para Cliente: {client_id}, SKU: {sku_id}, Fuente: {history_source}.")
        raise RuntimeError(f"No hay datos históricos disponibles para el pronóstico para Cliente: {client_id}, SKU: {sku_id}, Fuente: {history_source}.")

    history_df_for_processing = pd.DataFrame([
        {'unique_id': f"{item.client_id}-{item.sku_id}", 'ds': item.period, 'y': item.value}
        for item in historical_data_raw
    ])
    history_df_for_processing['ds'] = pd.to_datetime(history_df_for_processing['ds'])
    history_df_for_processing = history_df_for_processing.sort_values(by=['unique_id', 'ds']).reset_index(drop=True)

    # --- CAMBIO AQUÍ: Verificar el tamaño del dataset antes del pronóstico ---
    if history_df_for_processing.empty or len(history_df_for_processing) < MIN_FORECAST_POINTS:
        logger.warning(f"Dataset muy pequeño para pronóstico de Client: {client_id}, SKU: {sku_id}. Puntos: {len(history_df_for_processing)}")
        raise RuntimeError(f"Conjunto de datos histórico demasiado pequeño ({len(history_df_for_processing)} puntos). Se requieren al menos {MIN_FORECAST_POINTS} puntos para generar el pronóstico.")
    # --- FIN CAMBIO ---

    # --- CAMBIO AQUÍ: Calcular Historia Suavizada y Guardarla ---
    smoothed_history_df = calculate_smoothed_history(history_df_for_processing, smoothing_alpha)
    
    # Crear la KeyFigure "Historia Suavizada" si no existe
    db_kf_smoothed_history = crud.get_key_figure_by_name(db, "Historia Suavizada")
    if not db_kf_smoothed_history:
        db_kf_smoothed_history = crud.create_key_figure(
            db=db,
            key_figure=schemas.DimKeyFigureCreate(
                key_figure_id=3, # ID arbitrario, asegúrate de que sea único (ej. 3 para después de 1 y 2)
                name="Historia Suavizada",
                applies_to="history", # Aplica a history
                editable=False,
                order=3 
            )
        )
        logger.info("Created DimKeyFigure for 'Historia Suavizada'.")
    smoothed_history_kf_id = db_kf_smoothed_history.key_figure_id

    # Preparar y guardar registros de historia suavizada en fact_history
    smoothed_records_to_insert = []
    # Obtener un client_final_id de un registro histórico existente
    client_final_id_for_smoothed = historical_data_raw[0].client_final_id 

    for index, row in smoothed_history_df.iterrows():
        # Usar el mismo source que la historia cruda para la historia suavizada.
        # Esto asume que la historia suavizada se deriva de una fuente específica.
        smoothed_records_to_insert.append({
            "client_id": client_id,
            "sku_id": sku_id,
            "client_final_id": client_final_id_for_smoothed,
            "period": row['ds'].date(),
            "source": history_source, # Misma fuente que la historia original
            "key_figure_id": smoothed_history_kf_id,
            "value": row['y_smoothed'],
            "user_id": DEFAULT_USER_ID
        })
    
    try:
        raw_connection = db.connection().connection 
        cur = raw_connection.cursor()
        query_smoothed_history = """
            INSERT INTO fact_history (client_id, sku_id, client_final_id, period, source, key_figure_id, value, user_id)
            VALUES %s
            ON CONFLICT (client_id, sku_id, client_final_id, period, key_figure_id, source) DO UPDATE
            SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
        """
        smoothed_values_for_insert = [
            (r['client_id'], r['sku_id'], r['client_final_id'], r['period'], r['source'],
             r['key_figure_id'], r['value'], r['user_id'])
            for r in smoothed_records_to_insert
        ]
        extras.execute_values(cur, query_smoothed_history, smoothed_values_for_insert)
        logger.info(f"Insertados/actualizados {len(smoothed_records_to_insert)} registros de historia suavizada en fact_history.")
        # db.commit() no aquí, el commit final es después de ambos inserts (smoothed y forecast_stat)
    except Exception as e:
        logger.error(f"Error al insertar historia suavizada: {e}")
        db.rollback() 
        raise RuntimeError(f"Error al guardar la historia suavizada en la DB: {e}")
    # --- FIN CAMBIO ---


    # 2. Seleccionar y ejecutar el modelo de Forecast (ahora usa history_df_for_processing)
    model_class = FORECAST_MODELS.get(model_name)
    if not model_class:
        raise ValueError(f"Modelo de forecast '{model_name}' no soportado.")

    models_to_use = []
    if model_name == "ETS":
        models_to_use.append(model_class()) 
    elif model_name == "ARIMA":
        models_to_use.append(model_class(order=(0,1,0)))
    else:
        models_to_use.append(model_class())


    sf = StatsForecast(
        models=models_to_use,
        freq='MS',
        n_jobs=-1,
    )

    try:
        sf.fit(history_df_for_processing) # Usamos el DataFrame completo para el forecast
        forecast_df = sf.predict(h=forecast_horizon)
        logger.info(f"Forecast generado con éxito para Client: {client_id}, SKU: {sku_id}")
    except Exception as e:
        logger.error(f"Error al ejecutar el forecast para Client: {client_id}, SKU: {sku_id}: {e}")
        raise RuntimeError(f"Error en el motor de pronóstico: {e}")

    # 4. Guardar parámetros de la corrida de Forecast
    forecast_run_id = uuid.uuid4()
    crud.create_forecast_smoothing_parameter(
        db=db,
        forecast_run_id=forecast_run_id,
        client_id=client_id,
        alpha=smoothing_alpha,
        user_id=DEFAULT_USER_ID
    )
    logger.debug(f"Forecast smoothing parameter creado con ID: {forecast_run_id}")


    # 5. Guardar resultados en fact_forecast_stat
    forecast_model_column_name = model_name

    db_kf_stat_forecast = crud.get_key_figure_by_name(db, "Statistical Forecast")
    if not db_kf_stat_forecast:
        db_kf_stat_forecast = crud.create_key_figure(
            db=db,
            key_figure=schemas.DimKeyFigureCreate(
                key_figure_id=4, 
                name="Statistical Forecast",
                applies_to="forecast",
                editable=False,
                order=4 
            )
        )
        logger.info("Created DimKeyFigure for 'Statistical Forecast'.")
    statistical_forecast_kf_id = db_kf_stat_forecast.key_figure_id


    forecast_records = []
    for index, row in forecast_df.iterrows():
        client_final_id_from_history = historical_data_raw[0].client_final_id # Ya sabemos que history_data_raw no está vacío

        forecast_records.append({
            "client_id": client_id,
            "sku_id": sku_id,
            "client_final_id": client_final_id_from_history,
            "period": row['ds'].date(),
            "value": row[forecast_model_column_name],
            "model_used": model_name,
            "forecast_run_id": forecast_run_id,
            "user_id": DEFAULT_USER_ID
        })

    logger.debug(f"Preparados {len(forecast_records)} registros para fact_forecast_stat.")

    try:
        raw_connection = db.connection().connection 
        cur = raw_connection.cursor()              

        query = """
            INSERT INTO fact_forecast_stat (client_id, sku_id, client_final_id, period, value, model_used, forecast_run_id, user_id)
            VALUES %s
            ON CONFLICT (client_id, sku_id, client_final_id, period) DO UPDATE
            SET value = EXCLUDED.value, model_used = EXCLUDED.model_used, forecast_run_id = EXCLUDED.forecast_run_id, created_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
        """
        values_to_insert = [
            (r['client_id'], r['sku_id'], r['client_final_id'], r['period'], r['value'],
             r['model_used'], r['forecast_run_id'], r['user_id'])
            for r in forecast_records
        ]
        
        extras.execute_values(
            cur,
            query,
            values_to_insert
        )
        
        db.commit() # ¡COMMIT FINAL AQUÍ!
        
        logger.info(f"Insertados/actualizados {len(forecast_records)} registros en fact_forecast_stat.")
    except Exception as e:
        logger.error(f"Error al insertar en fact_forecast_stat: {e}")
        db.rollback() 
        raise RuntimeError(f"Error al guardar el pronóstico en la DB: {e}")

    logger.info(f"Forecast completado y guardado para Client: {client_id}, SKU: {sku_id}")
    return {"message": "Forecast generated and saved successfully", "forecast_run_id": forecast_run_id}