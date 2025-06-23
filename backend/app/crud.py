# backend/app/crud.py - Versión corregida para forecaist_schema.sql

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
import uuid

from . import models, schemas

# --- Operaciones CRUD para DimClients, DimSkus, DimKeyFigures (sin cambios) ---

def get_client_by_name(db: Session, client_name: str):
    return db.query(models.DimClient).filter(models.DimClient.client_name == client_name).first()

def get_client(db: Session, client_id: uuid.UUID):
    return db.query(models.DimClient).filter(models.DimClient.client_id == client_id).first()

def get_clients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DimClient).offset(skip).limit(limit).all()

def create_client(db: Session, client: schemas.DimClientCreate):
    db_client = models.DimClient(client_name=client.client_name)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_sku_by_name(db: Session, sku_name: str):
    return db.query(models.DimSku).filter(models.DimSku.sku_name == sku_name).first()

def get_sku(db: Session, sku_id: uuid.UUID):
    return db.query(models.DimSku).filter(models.DimSku.sku_id == sku_id).first()

def get_skus(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DimSku).offset(skip).limit(limit).all()

def create_sku(db: Session, sku: schemas.DimSkuCreate):
    db_sku = models.DimSku(sku_name=sku.sku_name)
    db.add(db_sku)
    db.commit()
    db.refresh(db_sku)
    return db_sku

def get_key_figure(db: Session, key_figure_id: int):
    return db.query(models.DimKeyFigure).filter(models.DimKeyFigure.key_figure_id == key_figure_id).first()

def get_key_figure_by_name(db: Session, name: str):
    return db.query(models.DimKeyFigure).filter(models.DimKeyFigure.name == name).first()

def get_key_figures(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DimKeyFigure).offset(skip).limit(limit).all()

def create_key_figure(db: Session, key_figure: schemas.DimKeyFigureCreate):
    db_key_figure = models.DimKeyFigure(
        key_figure_id=key_figure.key_figure_id,
        name=key_figure.name,
        applies_to=key_figure.applies_to,
        editable=key_figure.editable,
        order=key_figure.order
    )
    db.add(db_key_figure)
    db.commit()
    db.refresh(db_key_figure)
    return db_key_figure

# --- Operaciones CRUD para DimAdjustmentTypes (Nuevo/Base) ---
def get_adjustment_type(db: Session, adjustment_type_id: int):
    return db.query(models.DimAdjustmentType).filter(models.DimAdjustmentType.adjustment_type_id == adjustment_type_id).first()

# --- Operaciones CRUD para FactHistory (Actualizadas para 'source' en PK) ---
def get_fact_history(
    db: Session, 
    client_id: uuid.UUID, 
    sku_id: uuid.UUID, 
    client_final_id: uuid.UUID, 
    period: date, 
    key_figure_id: int,
    source: str # Añadido 'source' a la clave primaria
):
    return db.query(models.FactHistory).options(
        joinedload(models.FactHistory.client),
        joinedload(models.FactHistory.sku),
        joinedload(models.FactHistory.key_figure)
    ).filter(
        models.FactHistory.client_id == client_id,
        models.FactHistory.sku_id == sku_id,
        models.FactHistory.client_final_id == client_final_id,
        models.FactHistory.period == period,
        models.FactHistory.key_figure_id == key_figure_id,
        models.FactHistory.source == source # Filtrar por source
    ).first()

def get_fact_history_data(
    db: Session, 
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    key_figure_ids: Optional[List[int]] = None,
    sources: Optional[List[str]] = None, # Nuevo parámetro para filtrar por source
    skip: int = 0,
    limit: int = 100
) -> List[models.FactHistory]:
    query = db.query(models.FactHistory).options(
        joinedload(models.FactHistory.client),
        joinedload(models.FactHistory.sku),
        joinedload(models.FactHistory.key_figure)
    )
    if client_ids:
        query = query.filter(models.FactHistory.client_id.in_(client_ids))
    if sku_ids:
        query = query.filter(models.FactHistory.sku_id.in_(sku_ids))
    if start_period:
        query = query.filter(models.FactHistory.period >= start_period)
    if end_period:
        query = query.filter(models.FactHistory.period <= end_period)
    if key_figure_ids:
        query = query.filter(models.FactHistory.key_figure_id.in_(key_figure_ids))
    if sources: # Nuevo filtro por source
        query = query.filter(models.FactHistory.source.in_(sources))
    
    return query.offset(skip).limit(limit).all()

def create_fact_history(db: Session, fact_history: schemas.FactHistoryCreate, user_id: uuid.UUID):
    db_fact_history = models.FactHistory(
        client_id=fact_history.client_id,
        sku_id=fact_history.sku_id,
        client_final_id=fact_history.client_final_id,
        period=fact_history.period,
        source=fact_history.source,
        key_figure_id=fact_history.key_figure_id,
        value=fact_history.value,
        user_id=user_id
    )
    db.add(db_fact_history)
    db.commit()
    db.refresh(db_fact_history)
    return db_fact_history

def update_fact_history(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    source: str, # Añadido 'source' a los parámetros de identificación
    fact_history_update: schemas.FactHistoryBase,
    user_id: uuid.UUID
):
    db_fact_history = get_fact_history(db, client_id, sku_id, client_final_id, period, key_figure_id, source)
    if db_fact_history:
        for key, value in fact_history_update.model_dump(exclude_unset=True).items():
            setattr(db_fact_history, key, value)
        db_fact_history.updated_at = func.now()
        db_fact_history.user_id = user_id
        db.commit()
        db.refresh(db_fact_history)
    return db_fact_history

def delete_fact_history(
    db: Session, 
    client_id: uuid.UUID, 
    sku_id: uuid.UUID, 
    client_final_id: uuid.UUID, 
    period: date, 
    key_figure_id: int,
    source: str # Añadido 'source' a los parámetros de identificación
):
    db_fact_history = get_fact_history(db, client_id, sku_id, client_final_id, period, key_figure_id, source)
    if db_fact_history:
        db.delete(db_fact_history)
        db.commit()
    return db_fact_history


# --- Operaciones CRUD para Tablas Auxiliares y Hechos Adicionales (Básicas GET) ---
# Se incluyen solo para que el modelo SQLAlchemy esté completo y accesible si es necesario,
# pero no se les da soporte CRUD completo por ahora, a menos que lo pidas.

def get_forecast_smoothing_parameter(db: Session, forecast_run_id: uuid.UUID):
    return db.query(models.ForecastSmoothingParameter).filter(models.ForecastSmoothingParameter.forecast_run_id == forecast_run_id).first()

def get_forecast_version(db: Session, version_id: uuid.UUID):
    return db.query(models.ForecastVersion).filter(models.ForecastVersion.version_id == version_id).first()

def get_fact_forecast_stat_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.FactForecastStat).offset(skip).limit(limit).all()

def get_fact_adjustments_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.FactAdjustments).options(
        joinedload(models.FactAdjustments.client),
        joinedload(models.FactAdjustments.sku),
        joinedload(models.FactAdjustments.key_figure),
        joinedload(models.FactAdjustments.adjustment_type)
    ).offset(skip).limit(limit).all()

def get_fact_forecast_versioned_data_full(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.FactForecastVersioned).options(
        joinedload(models.FactForecastVersioned.version),
        joinedload(models.FactForecastVersioned.client),
        joinedload(models.FactForecastVersioned.sku),
        joinedload(models.FactForecastVersioned.key_figure)
    ).offset(skip).limit(limit).all()

def get_manual_input_comment_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ManualInputComment).offset(skip).limit(limit).all()