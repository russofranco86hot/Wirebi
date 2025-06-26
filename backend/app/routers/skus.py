# backend/app/routers/skus.py - Versión ACTUALIZADA para filtrar SKUs por cliente

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid # Asegurarse de importar uuid

from .. import crud, schemas, models # Asegúrate de que models esté importado si se usa DimSku en el router
from ..database import get_db

router = APIRouter(
    prefix="/skus",
    tags=["SKUs"]
)

# Helper function to validate and convert UUIDs from string (copied from sales_forecast.py if not already in a common util)
def validate_uuid_param(uuid_str: str, param_name: str):
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format for {param_name}. Must be a valid UUID string."
        )

@router.get("/", response_model=List[schemas.DimSku])
def read_skus_api(
    client_id: Optional[str] = Query(None, description="Filter SKUs by client UUID"), # Parámetro opcional
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve SKUs, optionally filtered by a client.
    """
    if client_id:
        validated_client_id = validate_uuid_param(client_id, "client_id")
        skus = crud.get_skus_by_client(db, validated_client_id, skip=skip, limit=limit)
    else:
        skus = crud.get_skus(db, skip=skip, limit=limit)
    
    if not skus:
        # Devuelve una lista vacía en lugar de 404 si no hay SKUs para un cliente específico
        # Esto permite que el dropdown se vacíe.
        return [] 
    return skus

@router.post("/", response_model=schemas.DimSku, status_code=status.HTTP_201_CREATED)
def create_sku_api(sku: schemas.DimSkuCreate, db: Session = Depends(get_db)):
    db_sku = crud.get_sku_by_name(db, sku_name=sku.sku_name)
    if db_sku:
        raise HTTPException(status_code=400, detail="SKU already registered")
    return crud.create_sku(db=db, sku=sku)