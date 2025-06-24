# backend/app/routers/sales_forecast.py - Versión corregida y completa

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import uuid

from .. import crud, schemas, models
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
    source: str, # Añadir source a la ruta para identificar
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
    source: str, # Añadir source a la ruta para identificar
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


# --- Endpoints para otras tablas de hechos y auxiliares ---
# Estos simplemente devuelven datos si existen, o una lista vacía si la tabla está vacía.

@router.get("/forecast_stat/", response_model=List[schemas.FactForecastStat])
def read_forecast_stat_data_api(
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"),
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    data = crud.get_fact_forecast_stat_data(db, client_ids, sku_ids, start_period, end_period, skip, limit)
    return data # Devuelve lista vacía si no hay datos

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
    data = crud.get_fact_adjustments_data(db, client_ids, sku_ids, start_period, end_period, key_figure_ids, adjustment_type_ids, skip, limit)
    return data # Devuelve lista vacía si no hay datos

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
    return data # Devuelve lista vacía si no hay datos

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
    return data # Devuelve lista vacía si no hay datos

@router.get("/versions/", response_model=List[schemas.ForecastVersion])
def read_forecast_versions_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    versions = crud.get_forecast_versions(db, skip=skip, limit=limit)
    return versions # Devuelve lista vacía si no hay datos

@router.get("/smoothing_parameters/", response_model=List[schemas.ForecastSmoothingParameter])
def read_forecast_smoothing_parameters_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    params = crud.get_forecast_smoothing_parameters(db, skip=skip, limit=limit)
    return params # Devuelve lista vacía si no hay datos

@router.get("/adjustment_types/", response_model=List[schemas.DimAdjustmentType])
def read_adjustment_types_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    types = crud.get_adjustment_types(db, skip=skip, limit=limit)
    return types # Devuelve lista vacía si no hay datos