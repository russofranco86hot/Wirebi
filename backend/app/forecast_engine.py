# backend/app/forecast_engine.py

from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import date, timedelta
import pandas as pd
from statsmodels.tsa.api import ExponentialSmoothing, SimpleExpSmoothing, Holt 
from statsmodels.tsa.arima.model import ARIMA 
import numpy as np
import uuid 
import logging 

from . import crud, models, schemas

logger = logging.getLogger(__name__) 

# Helper function to get dates in a range (first day of each month)
def get_dates_in_range(start_date: date, end_date: date) -> List[date]:
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)
    return dates

def calculate_manual_input_history(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    start_period: date,
    end_period: date,
    history_source: str = 'sales'
) -> List[schemas.CleanHistoryData]:
    """
    Calculates manual input history (formerly clean history) by fetching raw history
    and returning it in the CleanHistoryData schema (now representing 'Manual input').
    If there is an override adjustment for Manual input, it takes precedence.
    """
    # Se debe pedir la historia cruda (KEY_FIGURE_SALES_ID o KEY_FIGURE_ORDERS_ID)
    kf_id_for_raw_history_source = None
    if history_source == 'sales':
        kf_id_for_raw_history_source = schemas.KEY_FIGURE_SALES_ID
    elif history_source == 'order' or history_source == 'shipments':
        kf_id_for_raw_history_source = schemas.KEY_FIGURE_ORDERS_ID
    else:
        logger.warning(f"Fuente de historia '{history_source}' no reconocida para calcular manual input. Usando Sales como fallback.")
        kf_id_for_raw_history_source = schemas.KEY_FIGURE_SALES_ID

    # 1. Obtener historia cruda
    raw_history_entries = crud.get_fact_history_for_calculation(
        db=db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        source=history_source,
        key_figure_id=kf_id_for_raw_history_source
    )

    # 2. Obtener overrides para Manual input en el rango
    manual_input_overrides = crud.get_fact_adjustments_for_calculation(
        db=db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        key_figure_id=schemas.KEY_FIGURE_MANUAL_INPUT_ID,
        adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_OVERRIDE_ID]
    )
    # Mapear overrides por periodo para lookup rápido
    overrides_map = {adj.period: adj.value for adj in manual_input_overrides}

    manual_input_data_list = []
    for entry in raw_history_entries:
        if entry.value is None:
            continue
        # Si hay override para este periodo, usarlo
        value_to_use = overrides_map.get(entry.period, entry.value)
        manual_input_data_list.append(schemas.CleanHistoryData(
            client_id=entry.client_id,
            sku_id=entry.sku_id,
            client_final_id=client_final_id,
            period=entry.period,
            value=value_to_use,
            clientName=entry.client.client_name if entry.client else None,
            skuName=entry.sku.sku_name if entry.sku else None,
            keyFigureName="Manual input"
        ))
    return manual_input_data_list

def generate_forecast(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    history_source: str,
    smoothing_alpha: float,
    model_name: str,
    forecast_horizon: int,
    user_id: uuid.UUID 
) -> Dict[str, Any]:
    """
    Generates a statistical forecast for a given SKU-Client pair.
    Uses 'Manual input' KF (ID 5) as the base for forecasting if available, otherwise raw history.
    """
    end_history_period = date.today().replace(day=1) - timedelta(days=1) 
    start_history_period = (end_history_period - timedelta(days=365 * 3)).replace(day=1)
    
    # Priorizamos 'Manual input' (ID 5) para la serie histórica base, ya que es la versión "limpia" y editable.
    manual_input_data_for_series = crud.get_fact_history_for_calculation(
        db=db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_history_period,
        end_period=end_history_period,
        source='sales', # Manual input suele ser 'sales'
        key_figure_id=schemas.KEY_FIGURE_MANUAL_INPUT_ID
    )
    
    history_series = None
    if manual_input_data_for_series: # Si hay datos de 'Manual input', usarlos
        history_series_manual_input = pd.Series(
            [d.value for d in manual_input_data_for_series if d.value is not None], # Filtrar None
            index=[d.period for d in manual_input_data_for_series if d.value is not None]
        ).asfreq('MS')
        history_series = history_series_manual_input.fillna(method='ffill').fillna(method='bfill').fillna(0)
    else: # Si no hay datos de 'Manual input', usar la fuente raw elegida
        kf_id_for_raw_base = None
        if history_source == 'sales':
            kf_id_for_raw_base = schemas.KEY_FIGURE_SALES_ID
        elif history_source == 'order' or history_source == 'shipments':
            kf_id_for_raw_base = schemas.KEY_FIGURE_ORDERS_ID
        
        if kf_id_for_raw_base:
            history_base_data = crud.get_fact_history_for_calculation(
                db=db,
                client_id=client_id,
                sku_id=sku_id,
                client_final_id=client_id,
                start_period=start_history_period,
                end_period=end_history_period,
                source=history_source,
                key_figure_id=kf_id_for_raw_base # Obtener la KF raw correspondiente a la fuente
            )
            if history_base_data:
                history_series_raw_base = pd.Series(
                    [d.value for d in history_base_data if d.value is not None], 
                    index=[d.period for d in history_base_data if d.value is not None]
                ).asfreq('MS')
                history_series = history_series_raw_base.fillna(method='ffill').fillna(method='bfill').fillna(0)

    if history_series is None or history_series.empty or history_series.isnull().all():
        raise RuntimeError("La serie histórica está vacía o contiene solo valores nulos. No se puede generar el pronóstico.")
    
    forecast_values = []
    
    if model_name == "ETS":
        seasonal_periods = 12 
        if len(history_series) < (2 * seasonal_periods):
            try:
                model = SimpleExpSmoothing(history_series, initialization_method="estimated").fit(
                    smoothing_level=smoothing_alpha 
                )
                forecast_values = model.forecast(steps=forecast_horizon)
            except Exception as e:
                 raise RuntimeError(f"Error al ajustar o pronosticar con modelo SES (sin estacionalidad): {e}")
        else:
            try:
                model = ExponentialSmoothing(
                    history_series, 
                    seasonal_periods=seasonal_periods,
                    trend='add',          
                    seasonal='add',       
                    initialization_method="estimated"
                ).fit(smoothing_level=smoothing_alpha)
                
                forecast_values = model.forecast(steps=forecast_horizon)
            except Exception as e:
                raise RuntimeError(f"Error al ajustar o pronosticar con modelo ETS (estacional): {e}")
    
    elif model_name == "ARIMA":
        arima_series = history_series 
        if arima_series.empty:
            raise RuntimeError("La serie para el modelo ARIMA está vacía después de eliminar NaN.")
        
        order = (1,1,1) 
        try:
            model = ARIMA(arima_series, order=order).fit()
            forecast_values = model.predict(start=len(arima_series), end=len(arima_series) + forecast_horizon - 1)
        except Exception as e:
            raise RuntimeError(f"Error al ajustar o pronosticar con modelo ARIMA (orden {order}): {e}")
    
    else:
        raise ValueError("Modelo de pronóstico no soportado.")

    forecast_run_id = uuid.uuid4()
    
    crud.create_forecast_smoothing_parameter(
        db=db,
        forecast_run_id=forecast_run_id,
        client_id=client_id,
        alpha=smoothing_alpha,
        user_id=user_id 
    )

    forecast_records = []
    last_history_date = history_series.index[-1].date() if not history_series.empty else start_history_period
    
    stat_forecast_kf_id = None
    if history_source == 'sales':
        stat_forecast_kf_id = schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID
    elif history_source == 'order' or history_source == 'shipments':
        stat_forecast_kf_id = schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID
    else:
        # Fallback si la fuente no es reconocida, o un error si no debería ocurrir
        logger.warning(f"Fuente de historia '{history_source}' no reconocida para asignar ID de pronóstico estadístico. Usando Sales Stat Forecast como fallback.")
        stat_forecast_kf_id = schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID


    for i, value in enumerate(forecast_values):
        current_forecast_date = (pd.to_datetime(last_history_date) + pd.DateOffset(months=i+1)).date()

        forecast_records.append({
            "client_id": client_id,
            "sku_id": sku_id,
            "client_final_id": client_id, 
            "period": current_forecast_date,
            "value": float(value), 
            "model_used": model_name,
            "forecast_run_id": forecast_run_id,
            "user_id": user_id,
            "key_figure_id": stat_forecast_kf_id 
        })
    
    crud.create_fact_forecast_stat_batch(db=db, forecast_records=forecast_records)

    return {"status": "success", "forecast_run_id": str(forecast_run_id), "forecast_periods": len(forecast_records)}


def calculate_final_forecast(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    start_period: date,
    end_period: date
) -> List[schemas.FinalForecastData]:
    """
    Calculates the final forecast by applying manual adjustments (cantidad, porcentaje, override)
    to the statistical forecast.
    """
    logger.info(f"--- Entering calculate_final_forecast for Client: {client_id}, SKU: {sku_id}, Period: {start_period} to {end_period} ---")

    # Obtener Pronósticos Estadísticos de Sales y Orders
    stat_forecasts_sales = crud.get_fact_forecast_stat_data(
        db=db, client_ids=[client_id], sku_ids=[sku_id],
        start_period=start_period, end_period=end_period,
        key_figure_ids=[schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID]
    )
    stat_forecasts_orders = crud.get_fact_forecast_stat_data(
        db=db, client_ids=[client_id], sku_ids=[sku_id],
        start_period=start_period, end_period=end_period,
        key_figure_ids=[schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID]
    )
    all_stat_forecasts = stat_forecasts_sales + stat_forecasts_orders
    logger.info(f"Fetched {len(all_stat_forecasts)} raw statistical forecasts (Sales & Orders).")


    manual_adjustments = crud.get_fact_adjustments_for_calculation(
        db=db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_QTY_ID, schemas.ADJUSTMENT_TYPE_PCT_ID, schemas.ADJUSTMENT_TYPE_OVERRIDE_ID]
    )
    logger.info(f"Fetched {len(manual_adjustments)} total manual adjustments. Details:")
    for adj in manual_adjustments:
        logger.info(f"  - Adj Period: {adj.period}, KF_ID: {adj.key_figure_id}, AdjType_ID: {adj.adjustment_type_id}, Value: {adj.value}")


    # Fetch all relevant history data to use as base for historical periods of Final Forecast
    # Asumimos que 'Manual input' (ID 5) es la base para los ajustes históricos si existe,
    # o 'Sales' (ID 1) si no.
    historical_base_kfs = [
        schemas.KEY_FIGURE_SALES_ID,
        schemas.KEY_FIGURE_ORDERS_ID,
        schemas.KEY_FIGURE_SMOOTHED_SALES_ID,
        schemas.KEY_FIGURE_SMOOTHED_ORDERS_ID,
        schemas.KEY_FIGURE_MANUAL_INPUT_ID 
    ]
    all_history_data_from_db = crud.get_fact_history_for_calculation(
        db=db,
        client_id=client_id,
        sku_id=sku_id,
        start_period=start_period,
        end_period=end_period,
        source='sales', # Asumimos la fuente principal para estas bases históricas
        key_figure_ids=historical_base_kfs # Obtener todas estas figuras históricas
    )
    history_map = { (item.period, item.key_figure_id): item.value for item in all_history_data_from_db if item.period is not None and item.value is not None}
    logger.info(f"Historical base map built with {len(history_map)} entries.")


    # Prepare DataFrames for easier lookup
    stat_forecast_cols = ['period', 'value', 'client_id', 'sku_id', 'client_final_id', 'key_figure_id'] # Añadir key_figure_id
    adj_cols = ['period', 'value', 'key_figure_id', 'adjustment_type_id']

    if all_stat_forecasts: 
        forecast_df = pd.DataFrame([
            {'period': f.period, 'value': f.value, 'client_id': f.client_id, 'sku_id': f.sku_id, 'client_final_id': f.client_final_id, 'key_figure_id': f.key_figure_id}
            for f in all_stat_forecasts
        ]).set_index('period')
    else:
        forecast_df = pd.DataFrame(columns=stat_forecast_cols).set_index('period')
    
    if manual_adjustments:
        adjustments_df = pd.DataFrame([
            {'period': a.period, 'value': a.value, 'key_figure_id': a.key_figure_id, 'adjustment_type_id': a.adjustment_type_id}
            for a in manual_adjustments
        ]).set_index('period')
    else:
        adjustments_df = pd.DataFrame(columns=adj_cols).set_index('period')


    final_forecast_list = []

    forecast_start_date = None
    if not forecast_df.empty:
        forecast_start_date = forecast_df.index.min() 
    logger.info(f"Derived statistical forecast start date: {forecast_start_date}")

    all_periods_in_range = get_dates_in_range(start_period, end_period)
    
    for period in all_periods_in_range:
        current_base_value = None
        period_is_historical = (forecast_start_date is None) or (period < forecast_start_date)

        if period_is_historical:
            manual_input_val = history_map.get((period, schemas.KEY_FIGURE_MANUAL_INPUT_ID))
            if manual_input_val is not None:
                current_base_value = manual_input_val
            else: # Si no hay 'Manual input', usar 'Sales' como historia cruda base
                current_base_value = history_map.get((period, schemas.KEY_FIGURE_SALES_ID))
            logger.debug(f"Period {period}: Historical. Base from history_map (Manual Input/Sales): {current_base_value}")
        else:
            stat_sales_val = forecast_df.loc[(period, schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID), 'value'] if (period, schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID) in forecast_df.index else None
            stat_orders_val = forecast_df.loc[(period, schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID), 'value'] if (period, schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID) in forecast_df.index else None
            
            if stat_sales_val is not None and stat_orders_val is not None:
                current_base_value = float(stat_sales_val) + float(stat_orders_val) 
            elif stat_sales_val is not None:
                current_base_value = float(stat_sales_val)
            elif stat_orders_val is not None:
                current_base_value = float(stat_orders_val)
            
            logger.debug(f"Period {period}: Forecast. Base from stat forecast (Sales/Orders): {current_base_value}")
        
        if current_base_value is None:
            logger.debug(f"Period {period}: No base value found, adding None to final forecast.")
            final_forecast_list.append(schemas.FinalForecastData(
                client_id=client_id, sku_id=sku_id, client_final_id=client_final_id,
                period=period, value=None
            ))
            continue 


        adjusted_value = current_base_value
        logger.debug(f"Period {period}: Initial adjusted_value (base): {adjusted_value}")

        period_adjustments_df = pd.DataFrame(columns=['key_figure_id', 'adjustment_type_id', 'value'])

        if period in adjustments_df.index:
            period_adjustments_df = adjustments_df.loc[[period]] 
            if isinstance(period_adjustments_df, pd.Series): 
                period_adjustments_df = pd.DataFrame([period_adjustments_df.to_dict()])
            logger.debug(f"Period {period}: Raw adjustments for this period:\n{period_adjustments_df.to_string()}")


        if not period_adjustments_df.empty: 
            old_adjusted_value = adjusted_value 
            
            override_applied = False

            override_general_adj = period_adjustments_df[
                (period_adjustments_df['key_figure_id'].isin([schemas.KEY_FIGURE_FINAL_FORECAST_ID, schemas.KEY_FIGURE_MANUAL_INPUT_ID])) &
                (period_adjustments_df['adjustment_type_id'] == schemas.ADJUSTMENT_TYPE_OVERRIDE_ID)
            ]
            if not override_general_adj.empty:
                adjusted_value = float(override_general_adj['value'].iloc[0]) 
                logger.info(f"Period {period}: Applied general override (Final/Manual Input). Old: {old_adjusted_value}, New: {adjusted_value}")
                override_applied = True
            else:
                if not period_is_historical: 
                    override_stat_sales_kf_adj = period_adjustments_df[
                        (period_adjustments_df['key_figure_id'] == schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID) &
                        (period_adjustments_df['adjustment_type_id'] == schemas.ADJUSTMENT_TYPE_OVERRIDE_ID)
                    ]
                    override_stat_orders_kf_adj = period_adjustments_df[
                        (period_adjustments_df['key_figure_id'] == schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID) &
                        (period_adjustments_df['adjustment_type_id'] == schemas.ADJUSTMENT_TYPE_OVERRIDE_ID)
                    ]
                    if not override_stat_sales_kf_adj.empty:
                        adjusted_value = float(override_stat_sales_kf_adj['value'].iloc[0])
                        logger.info(f"Period {period}: Applied STAT_FORECAST_SALES_ID override. New value: {adjusted_value}")
                        override_applied = True
                    elif not override_stat_orders_kf_adj.empty:
                        adjusted_value = float(override_stat_orders_kf_adj['value'].iloc[0])
                        logger.info(f"Period {period}: Applied STAT_FORECAST_ORDERS_ID override. New value: {adjusted_value}")
                        override_applied = True
            
            if not override_applied: 
                qty_adj = period_adjustments_df[
                    (period_adjustments_df['key_figure_id'].isin([schemas.KEY_FIGURE_FINAL_FORECAST_ID, schemas.KEY_FIGURE_MANUAL_INPUT_ID])) & 
                    (period_adjustments_df['adjustment_type_id'] == schemas.ADJUSTMENT_TYPE_QTY_ID)
                ]
                if not qty_adj.empty:
                    old_adjusted_value = adjusted_value 
                    adjusted_value += float(qty_adj['value'].iloc[0])
                    logger.debug(f"Period {period}: Applied quantity adjustment. Old: {old_adjusted_value}, New: {adjusted_value}")

                pct_adj = period_adjustments_df[
                    (period_adjustments_df['key_figure_id'].isin([schemas.KEY_FIGURE_FINAL_FORECAST_ID, schemas.KEY_FIGURE_MANUAL_INPUT_ID])) & 
                    (period_adjustments_df['adjustment_type_id'] == schemas.ADJUSTMENT_TYPE_PCT_ID)
                ]
                if not pct_adj.empty:
                    old_adjusted_value = adjusted_value 
                    adjusted_value *= (1 + float(pct_adj['value'].iloc[0]) / 100) 
                    logger.debug(f"Period {period}: Applied percentage adjustment. Old: {old_adjusted_value}, New: {adjusted_value}")
            else:
                logger.debug(f"Period {period}: Override (Final/Manual Input or Stat) was applied, skipping Quantity/Percentage adjustments.")


        final_forecast_list.append(schemas.FinalForecastData(
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id,
            period=period,
            value=adjusted_value
        ))
    
    logger.info(f"--- Exiting calculate_final_forecast. Final list size: {len(final_forecast_list)}. First entry value: {final_forecast_list[0].value if final_forecast_list else 'N/A'} ---")
    return final_forecast_list