# backend/app/routers/sales_forecast.py

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import uuid
import logging
from collections import defaultdict

from .. import crud, schemas, models, forecast_engine
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/data",
    tags=["Sales & Forecast Data"]
)

# Helper function to validate and convert UUIDs from string
def validate_uuid_param(uuid_str: str, param_name: str):
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format for {param_name}. Must be a valid UUID string."
        )

# --- Endpoints para FactHistory ---
@router.get("/history/", response_model=List[schemas.FactHistory])
def read_history_data(
    client_ids: List[str] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[str] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    sources: List[str] = Query([], description="Filter by source (e.g., 'sales', 'order')"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve historical sales data with various filters.
    """
    # Validar y convertir UUIDs
    validated_client_ids = [validate_uuid_param(uid, "client_id") for uid in client_ids] if client_ids else None
    validated_sku_ids = [validate_uuid_param(uid, "sku_id") for uid in sku_ids] if sku_ids else None

    data = crud.get_fact_history_data(
        db,
        client_ids=validated_client_ids,
        sku_ids=validated_sku_ids,
        start_period=start_period,
        end_period=end_period,
        key_figure_ids=key_figure_ids,
        sources=sources,
        skip=skip,
        limit=limit
    )
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No historical data found matching criteria")
    return data

@router.post("/history/", response_model=schemas.FactHistory, status_code=status.HTTP_201_CREATED)
def create_history_data(
    fact_history: schemas.FactHistoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new historical sales data entry.
    """
    user_id_for_creation = uuid.UUID('00000000-0000-0000-0000-000000000001') # Placeholder de usuario

    client_exists = crud.get_client(db, client_id=fact_history.client_id)
    sku_exists = crud.get_sku(db, sku_id=fact_history.sku_id)
    key_figure_exists = crud.get_key_figure(db, key_figure_id=fact_history.key_figure_id)

    if not client_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client ID not found")
    if not sku_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU ID not found")
    if not key_figure_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key Figure ID not found")

    existing_entry = crud.get_fact_history(
        db,
        client_id=fact_history.client_id,
        sku_id=fact_history.sku_id,
        client_final_id=fact_history.client_final_id,
        period=fact_history.period,
        key_figure_id=fact_history.key_figure_id,
        source=fact_history.source
    )
    if existing_entry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data entry with this primary key already exists")

    return crud.create_fact_history(db=db, fact_history=fact_history, user_id=user_id_for_creation)

@router.put("/history/", response_model=schemas.FactHistory)
def update_history_data(
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    source: str,
    fact_history_update: schemas.FactHistoryBase,
    db: Session = Depends(get_db)
):
    """
    Update an existing historical sales data entry.
    Requires all primary key components in the path/query for identification.
    """
    user_id_for_update = uuid.UUID('00000000-0000-0000-0000-000000000001') # Placeholder de usuario
    db_history = crud.update_fact_history(
        db,
        client_id=client_id,
        sku_id=sku_id,
        client_final_id=client_final_id,
        period=period,
        key_figure_id=key_figure_id,
        source=source,
        fact_history_update=fact_history_update,
        user_id=user_id_for_update
    )
    if db_history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historical data entry not found")
    return db_history

@router.delete("/history/", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_data(
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    source: str,
    db: Session = Depends(get_db)
):
    """
    Delete a historical sales data entry.
    """
    db_history = crud.delete_fact_history(
        db,
        client_id=client_id,
        sku_id=sku_id,
        client_final_id=client_final_id,
        period=period,
        key_figure_id=key_figure_id,
        source=source
    )
    if db_history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historical data entry not found")
    return {"message": "Historical data entry deleted successfully"}


# --- Endpoint para disparar la generación de Forecast Estadístico ---
@router.post("/forecast/generate/", response_model=dict, status_code=status.HTTP_201_CREATED)
def generate_forecast_api(
    request: Request,
    client_id_str: str = Query(..., alias="clientId", description="Client UUID for which to generate forecast"),
    sku_id_str: str = Query(..., alias="skuId", description="SKU UUID for which to generate forecast"),
    history_source: str = Query(..., alias="historySource", description="Source of historical data ('sales', 'shipments', or 'order')"), 
    smoothing_alpha: float = Query(0.5, ge=0.0, le=1.0, description="Alpha parameter for exponential smoothing (0.0 to 1.0)"),
    model_name: str = Query("ETS", description="Statistical model to use for forecast (e.g., 'ETS', 'ARIMA')"),
    forecast_horizon: int = Query(12, ge=1, description="Number of periods to forecast ahead"),
    db: Session = Depends(get_db)
):
    """
    Triggers the generation of a statistical forecast for a given SKU-Client.
    The generated forecast is stored in fact_forecast_stat.
    """
    logger.info(f"Raw query params received: {request.query_params}")

    client_id = validate_uuid_param(client_id_str, "clientId")
    sku_id = validate_uuid_param(sku_id_str, "skuId")

    db_client = crud.get_client(db, client_id=client_id)
    db_sku = crud.get_sku(db, sku_id=sku_id)
    if not db_client or not db_sku:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client or SKU not found.")

    if history_source not in ['sales', 'order', 'shipments']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid history_source. Must be 'sales', 'order', or 'shipments'.")

    user_id = uuid.UUID('00000000-0000-0000-0000-000000000001') 

    try:
        result = forecast_engine.generate_forecast(
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            history_source=history_source,
            smoothing_alpha=smoothing_alpha,
            model_name=model_name,
            forecast_horizon=forecast_horizon,
            user_id=user_id 
        )
        return {"message": "Pronóstico generado y guardado exitosamente", "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate forecast: {e}")
    except Exception as e:
        logger.error(f"Error during forecast generation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during forecast generation: {e}")

# --- Endpoints para FactForecastStat ---
@router.get("/forecast_stat/", response_model=List[schemas.FactForecastStat])
def read_forecast_stat_data_api(
    client_ids: List[str] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[str] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    forecast_run_ids: List[str] = Query([], description="Filter by specific forecast run UUIDs"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    # Validar y convertir UUIDs
    validated_client_ids = [validate_uuid_param(uid, "client_id") for uid in client_ids] if client_ids else None
    validated_sku_ids = [validate_uuid_param(uid, "sku_id") for uid in sku_ids] if sku_ids else None
    validated_forecast_run_ids = [validate_uuid_param(uid, "forecast_run_id") for uid in forecast_run_ids] if forecast_run_ids else None

    data = crud.get_fact_forecast_stat_data(db, validated_client_ids, validated_sku_ids, start_period, end_period, validated_forecast_run_ids, skip, limit)
    return data

@router.post("/adjustments/", response_model=schemas.FactAdjustments, status_code=status.HTTP_201_CREATED)
def create_adjustment_api(
    adjustment: schemas.FactAdjustmentsCreate,
    db: Session = Depends(get_db)
):
    user_id_for_adjustment = uuid.UUID('00000000-0000-0000-0000-000000000001') # Placeholder

    client_exists = crud.get_client(db, client_id=adjustment.client_id)
    sku_exists = crud.get_sku(db, sku_id=adjustment.sku_id)
    key_figure_exists = crud.get_key_figure(db, key_figure_id=adjustment.key_figure_id)
    adjustment_type_exists = crud.get_adjustment_type(db, adjustment_type_id=adjustment.adjustment_type_id)

    if not all([client_exists, sku_exists, key_figure_exists, adjustment_type_exists]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more related IDs (Client, SKU, Key Figure, Adjustment Type) not found.")

    try:
        db_adjustment = crud.upsert_fact_adjustment(db=db, adjustment=adjustment)
        return db_adjustment
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create or update adjustment: {e}")

# --- Endpoints para FactForecastVersioned ---
@router.get("/forecast/versioned/", response_model=List[schemas.FactForecastVersioned])
def read_forecast_versioned_data_api(
    version_ids: List[str] = Query([], description="Filter by forecast version UUIDs"),
    client_ids: List[str] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[str] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    # Validar y convertir UUIDs
    validated_version_ids = [validate_uuid_param(uid, "version_id") for uid in version_ids] if version_ids else None
    validated_client_ids = [validate_uuid_param(uid, "client_id") for uid in client_ids] if client_ids else None
    validated_sku_ids = [validate_uuid_param(uid, "sku_id") for uid in sku_ids] if sku_ids else None

    data = crud.get_fact_forecast_versioned_data(db, validated_version_ids, validated_client_ids, validated_sku_ids, start_period, end_period, key_figure_ids, skip, limit)
    return data

# --- NUEVO Endpoint para proveer datos a la tabla AG-Grid ---
# ...existing code...

@router.get("/sales_forecast_data", response_model=Dict[str, Any])
def get_sales_forecast_data_for_grid(
    client_id: uuid.UUID = Query(..., description="Client UUID"),
    sku_id: uuid.UUID = Query(..., description="SKU UUID"),
    client_final_id: uuid.UUID = Query(..., description="Client Final ID"), # Should be same as client_id for now
    start_period: date = Query(..., description="Start period (YYYY-MM-DD)"),
    end_period: date = Query(..., description="End period (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves and transforms sales and forecast data for AG-Grid display.
    Combines raw history, clean history, statistical forecast, and final forecast.
    """
    logger.info(f"--- get_sales_forecast_data_for_grid called for Client: {client_id}, SKU: {sku_id}, Period: {start_period} to {end_period} ---")
    try:
        # Fetch all relevant DimKeyFigures for mapping and order
        all_dim_key_figures = crud.get_key_figures(db)
        key_figure_name_map = {kf.key_figure_id: kf.name for kf in all_dim_key_figures}
        key_figure_order_map = {kf.name: kf.order for kf in all_dim_key_figures}
        logger.info(f"Fetched {len(all_dim_key_figures)} dim_keyfigures.")

        # 1. Fetch data from all relevant tables
        history_raw_data = crud.get_fact_history_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period,
            sources=['sales', 'order', 'shipments'],
            key_figure_ids=[schemas.KEY_FIGURE_SALES_ID, schemas.KEY_FIGURE_ORDERS_ID] # Fetch Sales and Orders raw
        )
        logger.info(f"Fetched {len(history_raw_data)} raw history records (Sales/Orders).")

        history_smoothed_sales_data = crud.get_fact_history_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period,
            sources=['sales'], # Smoothed sales is from sales source
            key_figure_ids=[schemas.KEY_FIGURE_SMOOTHED_SALES_ID]
        )
        logger.info(f"Fetched {len(history_smoothed_sales_data)} smoothed sales history records (KF_SMOOTHED_SALES).")

        history_smoothed_orders_data = crud.get_fact_history_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period,
            sources=['order', 'shipments'], # Smoothed orders is from order/shipments source
            key_figure_ids=[schemas.KEY_FIGURE_SMOOTHED_ORDERS_ID]
        )
        logger.info(f"Fetched {len(history_smoothed_orders_data)} smoothed orders history records (KF_SMOOTHED_ORDERS).")

        # 1. Obtén los datos originales
        forecast_stat_sales_data = crud.get_fact_forecast_stat_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period,
            key_figure_ids=[schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID]
        )
        logger.info(f"Fetched {len(forecast_stat_sales_data)} statistical forecast sales records.")

        forecast_stat_orders_data = crud.get_fact_forecast_stat_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period,
            key_figure_ids=[schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID]
        )
        logger.info(f"Fetched {len(forecast_stat_orders_data)} statistical forecast orders records.")


        manual_input_data = forecast_engine.calculate_manual_input_history( # Nuevo nombre de función
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id,
            start_period=start_period,
            end_period=end_period
        )
        logger.info(f"Fetched {len(manual_input_data)} manual input history records.")

        final_forecast_data = forecast_engine.calculate_final_forecast(
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id,
            start_period=start_period,
            end_period=end_period
        )
        logger.info(f"Fetched {len(final_forecast_data)} final forecast records.")

        all_comments = crud.get_manual_input_comment_data(
            db=db,
            client_ids=[client_id],
            sku_ids=[sku_id],
            start_period=start_period,
            end_period=end_period
        )
        logger.info(f"Fetched {len(all_comments)} comment records.")
        
        manual_adj_qty_values = crud.get_fact_adjustments_for_calculation(
            db=db, client_id=client_id, sku_id=sku_id, start_period=start_period, end_period=end_period,
            key_figure_id=schemas.KEY_FIGURE_FINAL_FORECAST_ID, adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_QTY_ID] # Ajustes a Final Forecast
        )
        logger.info(f"Fetched {len(manual_adj_qty_values)} manual quantity adjustment records.")

        manual_adj_pct_values = crud.get_fact_adjustments_for_calculation(
            db=db, client_id=client_id, sku_id=sku_id, start_period=start_period, end_period=end_period,
            key_figure_id=schemas.KEY_FIGURE_FINAL_FORECAST_ID, adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_PCT_ID] # Ajustes a Final Forecast
        )
        logger.info(f"Fetched {len(manual_adj_pct_values)} manual percentage adjustment records.")

        override_values = crud.get_fact_adjustments_for_calculation(
            db=db, client_id=client_id, sku_id=sku_id, start_period=start_period, end_period=end_period,
            key_figure_id=schemas.KEY_FIGURE_FINAL_FORECAST_ID, # Override a Final Forecast
            adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_OVERRIDE_ID]
        )
        logger.info(f"Fetched {len(override_values)} override adjustment records.")


        # 2. Consolidate all data into a flat list of dictionaries with consistent keys
        consolidated_data = []

        # Process Sales (raw history)
        for item in history_raw_data:
            if item.source == 'sales': # Solo Sales como figura clave 'Sales'
                consolidated_data.append({
                    "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                    "period": item.period, "key_figure_id": schemas.KEY_FIGURE_SALES_ID,
                    "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_SALES_ID, "Sales"),
                    "value": item.value
                })
            elif item.source == 'order' or item.source == 'shipments': # Orders/Shipments como figura clave 'Orders'
                consolidated_data.append({
                    "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                    "period": item.period, "key_figure_id": schemas.KEY_FIGURE_ORDERS_ID,
                    "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_ORDERS_ID, "Orders"),
                    "value": item.value
                })

        # Process Smoothed Sales
        for item in history_smoothed_sales_data:
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_SMOOTHED_SALES_ID,
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_SMOOTHED_SALES_ID, "Smoothed Sales"),
                "value": item.value
            })
        # Process Smoothed Orders
        for item in history_smoothed_orders_data:
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_SMOOTHED_ORDERS_ID,
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_SMOOTHED_ORDERS_ID, "Smoothed Orders"),
                "value": item.value
            })
        # 2. Obtén los overrides para ambos Key Figures
        stat_sales_overrides = crud.get_fact_adjustments_for_calculation(
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            start_period=start_period,
            end_period=end_period,
            key_figure_id=schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID,
            adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_OVERRIDE_ID]
        )
        stat_orders_overrides = crud.get_fact_adjustments_for_calculation(
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            start_period=start_period,
            end_period=end_period,
            key_figure_id=schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID,
            adjustment_type_ids=[schemas.ADJUSTMENT_TYPE_OVERRIDE_ID]
        )
        stat_sales_overrides_map = {adj.period: adj.value for adj in stat_sales_overrides}
        stat_orders_overrides_map = {adj.period: adj.value for adj in stat_orders_overrides}


        # 3. Al consolidar los datos, aplica el override si existe
        # Para "Statistical forecast Sales"
        for item in forecast_stat_sales_data:
            value_to_use = stat_sales_overrides_map.get(item.period, item.value)
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID, 
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_STAT_FORECAST_SALES_ID, "Statistical forecast Sales"),
                "value": value_to_use
            })
        # Para "Statistical forecast Orders"
        for item in forecast_stat_orders_data:
            value_to_use = stat_orders_overrides_map.get(item.period, item.value)
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID, 
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_STAT_FORECAST_ORDERS_ID, "Statistical forecast Orders"),
                "value": value_to_use
            })
        
        # Process Manual input (from clean_history_data)
        for item in manual_input_data: # clean_history_data from forecast_engine.calculate_manual_input_history
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_MANUAL_INPUT_ID, 
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_MANUAL_INPUT_ID, "Manual input"),
                "value": item.value
            })

        # Process FinalForecastData 
        for item in final_forecast_data:
            consolidated_data.append({
                "client_id": item.client_id, "sku_id": item.sku_id, "client_final_id": item.client_final_id,
                "period": item.period, "key_figure_id": schemas.KEY_FIGURE_FINAL_FORECAST_ID, 
                "key_figure_name": key_figure_name_map.get(schemas.KEY_FIGURE_FINAL_FORECAST_ID, "Final Forecast"),
                "value": item.value
            })
        
        logger.info(f"Consolidated data count: {len(consolidated_data)} records.")


        if not consolidated_data:
            logger.info("No consolidated data, returning empty rows and columns.")
            return {"rows": [], "columns": []}

        # 3. Prepare data for pivoting into rows and columns
        unique_periods = sorted(list(set(item["period"] for item in consolidated_data)))
        logger.info(f"Unique periods found: {len(unique_periods)}.")
        
        sorted_key_figure_names_for_rows = sorted(
            list(set(item["key_figure_name"] for item in consolidated_data)),
            key=lambda name: key_figure_order_map.get(name, 999) 
        )
        logger.info(f"Sorted key figure names for rows: {len(sorted_key_figure_names_for_rows)}.")

        # Map for comments to quickly check if a cell has comments
        comments_map_for_grid = defaultdict(bool)
        for comment in all_comments:
            key = f"{comment.client_id}-{comment.sku_id}-{comment.period.isoformat()}-{comment.key_figure_id}"
            comments_map_for_grid[key] = True
        logger.info(f"Comments map populated with {len(comments_map_for_grid)} entries.")

        # IDs de históricos y pronóstico
        HISTORICAL_KF_IDS = [1, 2, 3, 4, 5]
        FORECAST_KF_IDS = [6, 7, 8]

        # Al armar las filas para la grilla:
        all_kf_ids = HISTORICAL_KF_IDS + FORECAST_KF_IDS
        all_kf_names = [key_figure_name_map[kf_id] for kf_id in all_kf_ids]


        grid_rows_final = []
        for kf_id in all_kf_ids:
            kf_name = key_figure_name_map[kf_id]
            current_row = {
                "keyFigureName": kf_name,
                "client_id": client_id,
                "sku_id": sku_id,
                "client_final_id": client_final_id,
                "clientName": crud.get_client(db, client_id).client_name if crud.get_client(db, client_id) else "N/A",
                "skuName": crud.get_sku(db, sku_id).sku_name if crud.get_sku(db, sku_id) else "N/A"
            }
            for period in unique_periods:
                period_iso = period.isoformat()
                data_field_name = f"date_{period_iso}"

                # Para históricos: siempre mostrar lo que haya
                if kf_id in HISTORICAL_KF_IDS:
                    value_for_cell = next(
                        (item["value"] for item in consolidated_data 
                        if item["key_figure_id"] == kf_id and item["period"] == period),
                        None
                    )
                    current_row[data_field_name] = value_for_cell

                # Para forecast: solo mostrar si hay forecast generado
                elif kf_id in FORECAST_KF_IDS:
                    value_for_cell = next(
                        (item["value"] for item in consolidated_data 
                        if item["key_figure_id"] == kf_id and item["period"] == period),
                        None
                    )
                    # Solo mostrar si hay forecast generado (es decir, si value_for_cell no es None)
                    current_row[data_field_name] = value_for_cell if value_for_cell is not None else None

                # ... lógica para comentarios, etc ...
            grid_rows_final.append(current_row)
            logger.info(f"Final grid rows generated: {len(grid_rows_final)} rows.")

        # --- AJUSTE: Generar columnas: Key Figure + meses ---
        dynamic_columns_for_grid = [
            {
                "headerName": "Key Figure",
                "field": "keyFigureName",
                "pinned": "left",
                "editable": False  # El frontend decide si es editable
            }
        ]
        for period in unique_periods:
            period_iso = period.isoformat()
            period_header = period.strftime('%b %Y')
            dynamic_columns_for_grid.append({
                "headerName": period_header,
                "field": f"date_{period_iso}",
                "colId": f"date_{period_iso}",
                # "editable": False,  # El frontend decide si es editable
                "type": "numericColumn"
            })

        logger.info(f"Dynamic columns generated: {len(dynamic_columns_for_grid)} columns.")

        return {
            "rows": grid_rows_final,
            "columns": dynamic_columns_for_grid
        }

    except Exception as e:
        logger.error(f"Error getting sales forecast data for grid: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sales forecast data: {e}")

# ...existing code...

# --- Endpoints para ForecastSmoothingParameters ---
@router.get("/smoothing_parameters/", response_model=List[schemas.ForecastSmoothingParameter])
def read_forecast_smoothing_parameters_api(
    client_id: Optional[uuid.UUID] = Query(None, description="Filter parameters by client UUID"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    query = db.query(models.ForecastSmoothingParameter)
    if client_id:
        query = query.filter(models.ForecastSmoothingParameter.client_id == client_id)
    params = query.offset(skip).limit(limit).all()
    return params

# --- Endpoints para DimAdjustmentTypes ---
@router.get("/adjustment_types/", response_model=List[schemas.DimAdjustmentType])
def read_adjustment_types_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    types = crud.get_adjustment_types(db, skip, limit)
    return types

@router.get("/forecast/versions", response_model=List[schemas.ForecastVersion])
def get_forecast_versions_api(
    client_id: Optional[uuid.UUID] = Query(None, description="UUID del cliente"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Devuelve una lista de versiones de pronóstico.
    """
    return crud.get_forecast_versions(db=db, client_id=client_id, skip=skip, limit=limit)