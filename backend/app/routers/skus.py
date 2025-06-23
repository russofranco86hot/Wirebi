from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(
    prefix="/skus",
    tags=["SKUs"]
)

@router.post("/", response_model=schemas.DimSku)
def create_sku(sku: schemas.DimSkuCreate, db: Session = Depends(get_db)):
    db_sku = crud.get_sku_by_name(db, sku_name=sku.sku_name)
    if db_sku:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU name already registered")
    return crud.create_sku(db=db, sku=sku)

@router.get("/", response_model=List[schemas.DimSku])
def read_skus(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    skus = crud.get_skus(db, skip=skip, limit=limit)
    return skus

@router.get("/{sku_id}", response_model=schemas.DimSku)
def read_sku(sku_id: uuid.UUID, db: Session = Depends(get_db)):
    db_sku = crud.get_sku(db, sku_id=sku_id)
    if db_sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    return db_sku