# backend/app/routers/sales_forecast.py - Versión corregida

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
        # Se devuelve un 404 si no hay datos, como lo estaba haciendo.
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


# --- NO INCLUIMOS ENDPOINTS ESPECÍFICOS PARA FORECAST_VERSIONED O STAT EN ESTE ROUTER ---
# Si en el futuro necesitas endpoints para estas tablas, los crearemos.
# Por ahora, nos enfocamos en fact_history como la fuente principal de datos.