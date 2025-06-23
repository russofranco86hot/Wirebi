from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import uuid # Necesitas importar uuid aquí para usarlo en la conversión

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(
    prefix="/data",
    tags=["Sales & Forecast Data"]
)

# --- Endpoints para FactHistory ---
@router.get("/history/", response_model=List[schemas.FactHistory])
def read_history_data(
    # CAMBIO CRUCIAL: FastAPI parseará automáticamente a List[uuid.UUID]
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"), # Default a lista vacía
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),       # Default a lista vacía
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"), # Default a lista vacía
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve historical sales data with various filters.
    """
    # NO NECESITAS PARSEAR AHORA, FastAPI ya lo hizo.
    # Los argumentos client_ids y sku_ids ya serán List[uuid.UUID] o List[int]
    
    data = crud.get_fact_history_data(
        db,
        client_ids=client_ids, # Usamos los IDs directamente
        sku_ids=sku_ids,       # Usamos los IDs directamente
        start_period=start_period,
        end_period=end_period,
        key_figure_ids=key_figure_ids,
        skip=skip,
        limit=limit
    )
    if not data:
        # Dejamos el 404 aquí, ya que el API devuelve 404 si no hay datos.
        # Si prefieres 200 OK y lista vacía, comenta esta línea.
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
        key_figure_id=fact_history.key_figure_id
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
        key_figure_id=key_figure_id
    )
    if db_history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historical data entry not found")
    return {"message": "Historical data entry deleted successfully"}


# --- Endpoints para FactForecastVersioned ---
@router.get("/forecast/versioned/", response_model=List[schemas.FactForecastVersioned])
def read_forecast_versioned_data(
    # CAMBIO CRUCIAL: FastAPI parseará automáticamente a List[uuid.UUID]
    version_ids: List[uuid.UUID] = Query([], description="Filter by forecast version UUIDs"), # Default a lista vacía
    client_ids: List[uuid.UUID] = Query([], description="Filter by client UUIDs"), # Default a lista vacía
    sku_ids: List[uuid.UUID] = Query([], description="Filter by SKU UUIDs"),       # Default a lista vacía
    start_period: Optional[date] = Query(None, description="Filter data from this period (YYYY-MM-DD)"),
    end_period: Optional[date] = Query(None, description="Filter data up to this period (YYYY-MM-DD)"),
    key_figure_ids: List[int] = Query([], description="Filter by KeyFigure IDs"), # Default a lista vacía
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve versioned forecast data with various filters.
    """
    # NO NECESITAS PARSEAR AHORA, FastAPI ya lo hizo.
    data = crud.get_fact_forecast_versioned_data(
        db,
        version_ids=version_ids,
        client_ids=client_ids,
        sku_ids=sku_ids,
        start_period=start_period,
        end_period=end_period,
        key_figure_ids=key_figure_ids,
        skip=skip,
        limit=limit
    )
    if not data:
        # Dejamos el 404 aquí, ya que el API devuelve 404 si no hay datos.
        # Si prefieres 200 OK y lista vacía, comenta esta línea.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No versioned forecast data found matching criteria")
    return data


@router.post("/forecast/versioned/", response_model=schemas.FactForecastVersioned, status_code=status.HTTP_201_CREATED)
def create_forecast_versioned_data(
    forecast_data: schemas.FactForecastVersionedCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new versioned forecast data entry.
    """
    version_exists = crud.get_forecast_version(db, version_id=forecast_data.version_id)
    client_exists = crud.get_client(db, client_id=forecast_data.client_id)
    sku_exists = crud.get_sku(db, sku_id=forecast_data.sku_id)
    key_figure_exists = crud.get_key_figure(db, key_figure_id=forecast_data.key_figure_id)

    if not version_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forecast Version ID not found")
    if not client_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client ID not found")
    if not sku_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU ID not found")
    if not key_figure_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key Figure ID not found")

    existing_entry = crud.get_fact_forecast_versioned(
        db,
        version_id=forecast_data.version_id,
        client_id=forecast_data.client_id,
        sku_id=forecast_data.sku_id,
        client_final_id=forecast_data.client_final_id,
        period=forecast_data.period,
        key_figure_id=forecast_data.key_figure_id
    )
    if existing_entry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data entry with this primary key already exists")

    return crud.create_fact_forecast_versioned(db=db, forecast_data=forecast_data)

@router.put("/forecast/versioned/", response_model=schemas.FactForecastVersioned)
def update_forecast_versioned_data(
    version_id: uuid.UUID,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    forecast_update: schemas.FactForecastVersionedBase,
    db: Session = Depends(get_db)
):
    """
    Update an existing versioned forecast data entry.
    """
    db_forecast = crud.update_fact_forecast_versioned(
        db,
        version_id=version_id,
        client_id=client_id,
        sku_id=sku_id,
        client_final_id=client_final_id,
        period=period,
        key_figure_id=key_figure_id,
        forecast_update=forecast_update
    )
    if db_forecast is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versioned forecast data entry not found")
    return db_forecast

@router.delete("/forecast/versioned/", status_code=status.HTTP_204_NO_CONTENT)
def delete_forecast_versioned_data(
    version_id: uuid.UUID,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a versioned forecast data entry.
    """
    db_forecast = crud.delete_fact_forecast_versioned(
        db,
        version_id=version_id,
        client_id=client_id,
        sku_id=sku_id,
        client_final_id=client_final_id,
        period=period,
        key_figure_id=key_figure_id
    )
    if db_forecast is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versioned forecast data entry not found")
    return {"message": "Versioned forecast data entry deleted successfully"}