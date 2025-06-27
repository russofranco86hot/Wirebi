# backend/app/forecast_engine.py - Versión con soporte para 'shipments',
#                                  cálculo de Historia Limpia y Pronóstico Final
#                                  MEJORADO: Logs de depuración, manejo de errores, NaN y client_final_id
#                                  AÑADIDO: Log de shape de forecast_df
#                                  CORREGIDO: FutureWarning de inplace=True

import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import ETS, ARIMA
from sqlalchemy.orm import Session
from datetime import date, timedelta
import uuid
import logging
from typing import List, Dict, Any, Optional

from . import models, crud, schemas
from psycopg2 import extras # Se mantiene la importación aunque no se use directamente en las nuevas funciones, se usaba en create_fact_forecast_stat_batch

logger = logging.getLogger(__name__)

# --- Definir DEFAULT_USER_ID aquí para que sea accesible en este módulo ---
DEFAULT_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')
# -------------------------------------------------------------------------

# --- Constantes para Key Figure IDs y Adjustment Type IDs ---
KF_SALES_ID = 1
KF_ORDER_ID = 2
KF_SHIPMENTS_ID = 3
KF_STATISTICAL_FORECAST_ID = 4
KF_CLEAN_HISTORY_ID = 5
KF_FINAL_FORECAST_ID = 6

ADJ_TYPE_MANUAL_QTY_ID = 1
ADJ_TYPE_MANUAL_PCT_ID = 2
ADJ_TYPE_OVERRIDE_ID = 3
ADJ_TYPE_CLEAN_BY_PCT_ID = 4
# -----------------------------------------------------------

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

    data_df = data_df.sort_values(by='ds')
    data_df['y_smoothed'] = data_df['y'].ewm(alpha=alpha, adjust=False).mean()
    return data_df

def generate_forecast(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    history_source: str,
    smoothing_alpha: float,
    model_name: str,
    forecast_horizon: int
) -> dict:
    """
    Genera un pronóstico estadístico para un SKU y Cliente dados,
    utilizando la historia de ventas, pedidos o envíos como base.
    """
    logger.info(f"Iniciando generación de pronóstico para Cliente {client_id}, SKU {sku_id} con fuente {history_source}, modelo {model_name} y horizonte {forecast_horizon} meses.")

    # Paso 1: Obtener la figura clave ID de la fuente histórica
    source_key_figure_map = {
        'sales': KF_SALES_ID,
        'order': KF_ORDER_ID,
        'shipments': KF_SHIPMENTS_ID
    }
    history_key_figure_id = source_key_figure_map.get(history_source)
    if history_key_figure_id is None:
        raise RuntimeError(f"Fuente histórica no válida: {history_source}")

    try:
        # Obtener toda la historia relevante para el par cliente-sku y fuente
        raw_history_data_query = crud.get_fact_history_data(
            db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            key_figure_ids=[history_key_figure_id],
            sources=[history_source]
        )
        
        if not raw_history_data_query:
            raise RuntimeError(f"No hay suficientes datos históricos de '{history_source}' para generar el pronóstico para Cliente {client_id}, SKU {sku_id}. Asegúrate de que los filtros seleccionados tienen datos.")

        # Convertir a DataFrame de Pandas para StatsForecast
        history_df = pd.DataFrame([
            {'unique_id': f"{item.client_id}-{item.sku_id}", 'ds': item.period, 'y': item.value}
            for item in raw_history_data_query
        ])
        
        # Asegurar que 'ds' sea datetime y 'y' sea numérico
        history_df['ds'] = pd.to_datetime(history_df['ds'])
        history_df['y'] = pd.to_numeric(history_df['y'])

        # Rellenar NaNs en la columna 'y' (valor) con 0 para evitar problemas en StatsForecast
        history_df['y'] = history_df['y'].fillna(0) # CORREGIDO: Eliminado inplace=True para FutureWarning

        logger.info(f"History DataFrame antes del pronóstico (head):\n{history_df.head().to_string()}")
        logger.info(f"History DataFrame info:\n{history_df.info()}")

        if history_df.empty or len(history_df) < MIN_FORECAST_POINTS:
            raise RuntimeError(f"Conjunto de datos demasiado pequeño ({len(history_df)} puntos). Se requieren al menos {MIN_FORECAST_POINTS} puntos para generar el pronóstico.")

        # Advertencia si los datos son constantes o tienen muy poca variabilidad
        if history_df['y'].nunique() <= 1:
             logger.warning(f"ADVERTENCIA: Los datos históricos para Cliente {client_id}, SKU {sku_id} son constantes o tienen muy poca variabilidad para el modelo {model_name}. Datos: {history_df['y'].tolist()}")

        # Solo necesitamos un unique_id para StatsForecast para este caso de un solo par Client-SKU
        history_df['unique_id'] = f"{client_id}-{sku_id}"

        # Preparar el modelo de pronóstico
        models_to_forecast = [FORECAST_MODELS[model_name]()]
        
        sf = StatsForecast(
            models=models_to_forecast,
            freq='MS' # Asumiendo frecuencia mensual ('MS' para Month Start)
        )

        sf.fit(history_df)
        forecast_df = sf.predict(h=forecast_horizon) # Aquí se solicita el horizonte

        logger.info(f"Forecast DataFrame después de la predicción (head):\n{forecast_df.head().to_string()}")
        logger.info(f"Forecast DataFrame columnas: {forecast_df.columns.tolist()}")
        logger.info(f"Forecast DataFrame Shape (filas, columnas): {forecast_df.shape}") # NUEVO LOG CLAVE

        forecast_records = []
        new_forecast_run_id = uuid.uuid4()

        crud.create_forecast_smoothing_parameter(
            db=db,
            forecast_run_id=new_forecast_run_id,
            client_id=client_id,
            alpha=smoothing_alpha,
            user_id=DEFAULT_USER_ID
        )

        for _, row in forecast_df.iterrows():
            model_output_column = model_name.lower()
            
            actual_output_column = None
            if model_output_column in row:
                actual_output_column = model_output_column
            else:
                matching_cols = [col for col in forecast_df.columns if col.lower().startswith(model_output_column)]
                if matching_cols:
                    actual_output_column = matching_cols[0]
                
            if not actual_output_column:
                 logger.error(f"Error: La columna de salida esperada '{model_output_column}' no se encontró en el DataFrame de pronóstico. Columnas disponibles: {forecast_df.columns.tolist()}")
                 raise RuntimeError(f"Error de salida del modelo: La columna del pronóstico para '{model_name}' no se encontró. Esto puede indicar un fallo del modelo o datos insuficientes/inadecuados.")
            
            forecast_value = row[actual_output_column]

            forecast_records.append({
                'client_id': client_id,
                'sku_id': sku_id,
                'client_final_id': raw_history_data_query[0].client_final_id if raw_history_data_query and raw_history_data_query[0].client_final_id else crud.get_client(db, client_id).client_id,
                'period': row['ds'].date(),
                'value': forecast_value,
                'model_used': model_name,
                'forecast_run_id': new_forecast_run_id,
                'user_id': DEFAULT_USER_ID
            })
        
        crud.create_fact_forecast_stat_batch(db, forecast_records)

        logger.info(f"Pronóstico generado y guardado exitosamente para Cliente {client_id}, SKU {sku_id}.")
        return {"message": "Pronóstico generado y guardado exitosamente.", "forecast_run_id": str(new_forecast_run_id)}

    except RuntimeError as e:
        logger.error(f"Error específico de ejecución del pronóstico: {e}")
        raise
    except KeyError as e:
        logger.error(f"KeyError al procesar el pronóstico: La columna '{e}' no se encontró en el pronóstico de StatsForecast. Esto indica un fallo en la generación del pronóstico por el modelo.", exc_info=True)
        raise RuntimeError(f"Error de procesamiento de pronóstico: La columna de salida del modelo '{e}' no se encontró. Verifica los datos históricos o el modelo de pronóstico.")
    except Exception as e:
        logger.error(f"Error inesperado en la generación del pronóstico: {e}", exc_info=True)
        raise RuntimeError(f"Error interno al generar el pronóstico: {e}. Por favor, revisa los logs del servidor para más detalles del traceback.")


def calculate_clean_history(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID, # Necesario para la PK en la DB
    start_period: date,
    end_period: date,
    history_source: str = 'sales', # Fuente de historia cruda
    cleaning_adj_type_ids: Optional[List[int]] = None # Tipos de ajuste que "limpian" la historia
) -> List[schemas.CleanHistoryData]:
    """
    Calcula la 'Historia Limpia' aplicando ajustes de limpieza a la historia cruda.
    """
    if cleaning_adj_type_ids is None:
        cleaning_adj_type_ids = [ADJ_TYPE_CLEAN_BY_PCT_ID] # Por defecto, usar 'Clean by Pct'

    # Obtener historia cruda (ej. 'Sales')
    raw_history = crud.get_fact_history_for_calculation(
        db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        source=history_source
    )

    # Obtener ajustes de limpieza
    cleaning_adjustments = crud.get_fact_adjustments_for_calculation(
        db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        key_figure_id=KF_SALES_ID, # Ajustes aplicados a la historia de ventas (Sales)
        adjustment_type_ids=cleaning_adj_type_ids
    )

    # Convertir a diccionarios para facilitar la manipulación por período
    history_map = {item.period: item.value for item in raw_history}
    adjustments_map = {item.period: item.value for item in cleaning_adjustments}

    clean_history_results = []
    # Iterar sobre el rango de fechas para asegurar continuidad y aplicar ajustes
    current_period = start_period
    while current_period <= end_period:
        raw_value = history_map.get(current_period, 0.0) # Si no hay dato, asumir 0
        cleaning_adj_value = adjustments_map.get(current_period, 0.0)

        # Lógica de limpieza: historia cruda - ajustes de limpieza
        clean_value = raw_value - cleaning_adj_value

        clean_history_results.append(schemas.CleanHistoryData(
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id, # Se asume el mismo client_final_id
            period=current_period,
            value=clean_value,
            clientName=raw_history[0].client.client_name if raw_history else "N/A",
            skuName=raw_history[0].sku.sku_name if raw_history else "N/A"
        ))
        # Mover al siguiente mes
        if current_period.month == 12:
            current_period = current_period.replace(year=current_period.year + 1, month=1, day=1)
        else:
            current_period = current_period.replace(month=current_period.month + 1, day=1)

    return clean_history_results

def calculate_final_forecast(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID, # Necesario para la PK en la DB
    start_period: date,
    end_period: date,
    forecast_key_figure_id: int = KF_STATISTICAL_FORECAST_ID, # Pronóstico base
    forecast_adj_type_ids: Optional[List[int]] = None # Tipos de ajuste que modifican el pronóstico
) -> List[schemas.FinalForecastData]:
    """
    Calcula el 'Pronóstico Final' aplicando ajustes al pronóstico estadístico base.
    """
    if forecast_adj_type_ids is None:
        forecast_adj_type_ids = [ADJ_TYPE_OVERRIDE_ID] # Por defecto, usar 'Override'

    # Obtener el pronóstico estadístico base
    statistical_forecast_data = crud.get_fact_forecast_stat_data(
        db,
        client_ids=[client_id],
        sku_ids=[sku_id],
        start_period=start_period,
        end_period=end_period
    )
    
    # Obtener ajustes que afectan al pronóstico (ej. Overrides)
    forecast_adjustments = crud.get_fact_adjustments_for_calculation(
        db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        key_figure_id=KF_STATISTICAL_FORECAST_ID, # Ajustes aplicados al pronóstico estadístico
        adjustment_type_ids=forecast_adj_type_ids
    )

    # Convertir a diccionarios para facilitar la manipulación por período
    forecast_map = {item.period: item.value for item in statistical_forecast_data}
    adjustments_map = {item.period: item.value for item in forecast_adjustments}

    final_forecast_results = []
    current_period = start_period
    while current_period <= end_period:
        statistical_value = forecast_map.get(current_period, 0.0)
        adjustment_value = adjustments_map.get(current_period, 0.0)

        # Lógica de Pronóstico Final: Pronóstico Estadístico + Ajustes (Override)
        final_value = statistical_value + adjustment_value # Asumimos que los overrides son aditivos

        final_forecast_results.append(schemas.FinalForecastData(
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id, # Se asume el mismo client_final_id
            period=current_period,
            value=final_value,
            clientName=statistical_forecast_data[0].client.client_name if statistical_forecast_data else "N/A",
            skuName=statistical_forecast_data[0].sku.sku_name if statistical_forecast_data else "N/A"
        ))
        # Mover al siguiente mes
        if current_period.month == 12:
            current_period = current_period.replace(year=current_period.year + 1, month=1, day=1)
        else:
            current_period = current_period.replace(month=current_period.month + 1, day=1)

    return final_forecast_results