from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(
    prefix="/clients",
    tags=["Clients"]
)

@router.post("/", response_model=schemas.DimClient)
def create_client(client: schemas.DimClientCreate, db: Session = Depends(get_db)):
    db_client = crud.get_client_by_name(db, client_name=client.client_name)
    if db_client:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client name already registered")
    return crud.create_client(db=db, client=client)

@router.get("/", response_model=List[schemas.DimClient])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    clients = crud.get_clients(db, skip=skip, limit=limit)
    return clients

@router.get("/{client_id}", response_model=schemas.DimClient)
def read_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    db_client = crud.get_client(db, client_id=client_id)
    if db_client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return db_client