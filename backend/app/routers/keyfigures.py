from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(
    prefix="/keyfigures",
    tags=["KeyFigures"]
)

@router.post("/", response_model=schemas.DimKeyFigure)
def create_key_figure(key_figure: schemas.DimKeyFigureCreate, db: Session = Depends(get_db)):
    db_kf = crud.get_key_figure(db, key_figure_id=key_figure.key_figure_id)
    if db_kf:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Key Figure ID already registered")
    # Alternativamente, puedes buscar por nombre si no quieres que el ID se pase en la creación
    # db_kf = crud.get_key_figure_by_name(db, name=key_figure.name)
    # if db_kf:
    #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Key Figure name already registered")
    return crud.create_key_figure(db=db, key_figure=key_figure)

@router.get("/", response_model=List[schemas.DimKeyFigure])
def read_key_figures(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    key_figures = crud.get_key_figures(db, skip=skip, limit=limit)
    return key_figures

@router.get("/{key_figure_id}", response_model=schemas.DimKeyFigure)
def read_key_figure(key_figure_id: int, db: Session = Depends(get_db)):
    db_kf = crud.get_key_figure(db, key_figure_id=key_figure_id)
    if db_kf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key Figure not found")
    return db_kf