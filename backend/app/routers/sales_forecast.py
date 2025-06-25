# backend/app/routers/sales_forecast.py - Versión FINAL y COMPLETA (con POST /data/adjustments/)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import uuid

from .. import crud, schemas, models, forecast_engine # Importa forecast_engine
from ..database import get_db

router = APIRouter(
    prefix="/data",
    tags=["Sales & Forecast Data"]
)

# --- Endpoints para FactHistory ---
@router.get("/history/", response_model=List[schemas.FactHistory])
def read_history_data(
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    sources: List[str] = Query([], description="Filter by source (e.g., 'sales', 'order')"), # Nuevo filtro
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve historical sales data with various filters.
    """
    data = crud.get_fact_history_data(
        db,
        client_ids=client_ids,
        sku_ids=sku_ids,
        start_period=start_period,
        end_period=end_period,
        key_figure_ids=key_figure_ids,
        sources=sources, # Pasar el nuevo filtro
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
    user_id_for_creation = uuid.UUID('00000000-0000-0000-0000-000000000001')
    
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
    user_id_for_update = uuid.UUID('00000000-0000-0000-0000-000000000001')
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
    client_id: uuid.UUID = Query(..., description="Client UUID for which to generate forecast"),
    sku_id: uuid.UUID = Query(..., description="SKU UUID for which to generate forecast"),
    history_source: str = Query(..., description="Source of historical data ('sales', 'shipments', or 'order')"), 
    smoothing_alpha: float = Query(0.5, ge=0.0, le=1.0, description="Alpha parameter for exponential smoothing (0.0 to 1.0)"),
    model_name: str = Query("ETS", description="Statistical model to use for forecast (e.g., 'ETS', 'ARIMA')"),
    forecast_horizon: int = Query(12, ge=1, description="Number of periods to forecast ahead"),
    db: Session = Depends(get_db)
):
    """
    Triggers the generation of a statistical forecast for a given SKU-Client.
    The generated forecast is stored in fact_forecast_stat.
    """
    db_client = crud.get_client(db, client_id=client_id)
    db_sku = crud.get_sku(db, sku_id=sku_id)
    if not db_client or not db_sku:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client or SKU not found.")
    
    if history_source not in ['sales', 'order', 'shipments']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid history_source. Must be 'sales', 'order', or 'shipments'.")

    try:
        result = forecast_engine.generate_forecast(
            db=db,
            client_id=client_id,
            sku_id=sku_id,
            history_source=history_source,
            smoothing_alpha=smoothing_alpha,
            model_name=model_name,
            forecast_horizon=forecast_horizon
        )
        return {"message": "Forecast generation requested successfully", "result": result}
    except RuntimeError as e: 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate forecast: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during forecast generation: {e}")

# --- Endpoints para FactForecastStat ---
@router.get("/forecast_stat/", response_model=List[schemas.FactForecastStat])
def read_forecast_stat_data_api(
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    forecast_run_ids: List[uuid.UUID] = Query([], description="Filter by specific forecast run UUIDs"), 
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    data = crud.get_fact_forecast_stat_data(db, client_ids, sku_ids, start_period, end_period, forecast_run_ids, skip, limit)
    return data

# --- Endpoints para FactAdjustments (¡Importante!) ---
@router.get("/adjustments/", response_model=List[schemas.FactAdjustments])
def read_adjustments_data_api(
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    adjustment_type_ids: List[int] = Query([], description="Filter by Adjustment Type IDs"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve manual adjustments data with various filters.
    """
    data = crud.get_fact_adjustments_data(db, client_ids, sku_ids, start_period, end_period, key_figure_ids, adjustment_type_ids, skip, limit)
    return data

@router.post("/adjustments/", response_model=schemas.FactAdjustments, status_code=status.HTTP_201_CREATED)
def create_adjustment_api(
    adjustment: schemas.FactAdjustmentsCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new manual adjustment entry.
    """
    user_id_for_adjustment = uuid.UUID('00000000-0000-0000-0000-000000000001') # Placeholder

    client_exists = crud.get_client(db, client_id=adjustment.client_id)
    sku_exists = crud.get_sku(db, sku_id=adjustment.sku_id)
    key_figure_exists = crud.get_key_figure(db, key_figure_id=adjustment.key_figure_id)
    adjustment_type_exists = crud.get_adjustment_type(db, adjustment_type_id=adjustment.adjustment_type_id)

    if not all([client_exists, sku_exists, key_figure_exists, adjustment_type_exists]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more related IDs (Client, SKU, Key Figure, Adjustment Type) not found.")

    try:
        db_adjustment = crud.create_fact_adjustment(db=db, adjustment=adjustment)
        return db_adjustment
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create adjustment: {e}")

# --- Endpoints para FactForecastVersioned ---
@router.get("/forecast/versioned/", response_model=List[schemas.FactForecastVersioned])
def read_forecast_versioned_data_api(
    version_ids: List[uuid.UUID] = Query([], description="Filter by forecast version UUIDs"),
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    data = crud.get_fact_forecast_versioned_data(db, version_ids, client_ids, sku_ids, start_period, end_period, key_figure_ids, skip, limit)
    return data

# --- Endpoints para ManualInputComments ---
@router.get("/comments/", response_model=List[schemas.ManualInputComment])
def read_manual_input_comments_api(
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    data = crud.get_manual_input_comment_data(db, client_ids, sku_ids, start_period, end_period, key_figure_ids, skip, limit)
    return data

# --- Endpoints para ForecastVersions ---
@router.get("/versions/", response_model=List[schemas.ForecastVersion])
def read_forecast_versions_api(
    client_id: Optional[uuid.UUID] = Query(None, description="Filter versions by client UUID"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    query = db.query(models.ForecastVersion)
    if client_id:
        query = query.filter(models.ForecastVersion.client_id == client_id)
    versions = query.offset(skip).limit(limit).all()
    return versions

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