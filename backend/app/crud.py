# backend/app/crud.py - Versión corregida y completa para todas las operaciones CRUD.
# NO debe contener ninguna definición de API (@router.get, etc.) ni declaración de APIRouter.

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct 
from typing import List, Optional, Dict, Any 
from datetime import date, datetime
import uuid
import psycopg2.extras # Para ejecutar valores en lote
from psycopg2 import extras

from . import models, schemas 

# Helper function to get raw connection from SQLAlchemy session
def get_raw_connection(db: Session):
    """Obtiene la conexión psycopg2 subyacente de la sesión de SQLAlchemy."""
    return db.connection().connection

# --- Operaciones CRUD para DimClients, DimSkus, DimKeyFigures ---

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
    return db.query(models.DimSku).filter(models.DimSku.sku_name == sku_name).first() # Changed from sku_name to name as per model

def get_sku(db: Session, sku_id: uuid.UUID):
    return db.query(models.DimSku).filter(models.DimSku.sku_id == sku_id).first()

def get_skus(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DimSku).offset(skip).limit(limit).all()

# Nueva función para obtener SKUs filtrados por cliente
def get_skus_by_client(db: Session, client_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.DimSku]:
    """
    Obtiene SKUs asociados a un cliente específico a través de fact_history.
    """
    return db.query(models.DimSku).distinct().join(models.FactHistory, models.DimSku.sku_id == models.FactHistory.sku_id).filter(
        models.FactHistory.client_id == client_id
    ).offset(skip).limit(limit).all()

def create_sku(db: Session, sku: schemas.DimSkuCreate):
    db_sku = models.DimSku(sku_name=sku.sku_name) # Changed from sku_name to name as per model
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

# --- Operaciones CRUD para DimAdjustmentTypes ---
def get_adjustment_type(db: Session, adjustment_type_id: int):
    return db.query(models.DimAdjustmentType).filter(models.DimAdjustmentType.adjustment_type_id == adjustment_type_id).first()

def get_adjustment_type_by_name(db: Session, name: str):
    return db.query(models.DimAdjustmentType).filter(models.DimAdjustmentType.name == name).first()

def get_adjustment_types(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DimAdjustmentType).offset(skip).limit(limit).all()

def create_adjustment_type(db: Session, adj_type: schemas.DimAdjustmentTypeCreate):
    db_adj_type = models.DimAdjustmentType(
        adjustment_type_id=adj_type.adjustment_type_id,
        name=adj_type.name
    )
    db.add(db_adj_type)
    db.commit()
    db.refresh(db_adj_type)
    return db_adj_type


# --- Operaciones CRUD para FactHistory ---
def get_fact_history(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    source: str
):
    return db.query(models.FactHistory).filter(
        models.FactHistory.client_id == client_id,
        models.FactHistory.sku_id == sku_id,
        models.FactHistory.client_final_id == client_final_id,
        models.FactHistory.period == period,
        models.FactHistory.key_figure_id == key_figure_id,
        models.FactHistory.source == source
    ).first()

def get_fact_history_data(
    db: Session,
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    key_figure_ids: Optional[List[int]] = None,
    sources: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.FactHistory]:
    """
    Obtiene datos de historial de ventas con varios filtros.
    """
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
    if sources:
        query = query.filter(models.FactHistory.source.in_(sources))

    return query.offset(skip).limit(limit).all()

# Función para obtener historial de datos para cálculos específicos
def get_fact_history_for_calculation(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    start_period: date,
    end_period: date,
    source: str,
    key_figure_id: Optional[int] = None,
    key_figure_ids: Optional[List[int]] = None
):
    query = db.query(models.FactHistory).filter(
        models.FactHistory.client_id == client_id,
        models.FactHistory.sku_id == sku_id,
        models.FactHistory.period >= start_period,
        models.FactHistory.period <= end_period,
        models.FactHistory.source == source
    )
    if key_figure_ids is not None:
        query = query.filter(models.FactHistory.key_figure_id.in_(key_figure_ids))
    elif key_figure_id is not None:
        query = query.filter(models.FactHistory.key_figure_id == key_figure_id)
    return query.all()


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
    source: str,
    fact_history_update: schemas.FactHistoryBase,
    user_id: uuid.UUID
):
    db_fact_history = get_fact_history(db, client_id, sku_id, client_final_id, period, key_figure_id, source)
    if db_fact_history:
        for key, value in fact_history_update.model_dump(exclude_unset=True).items():
            setattr(db_fact_history, key, value)
        db_fact_history.updated_at = func.now()
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
    source: str
):
    db_fact_history = get_fact_history(db, client_id, sku_id, client_final_id, period, key_figure_id, source)
    if db_fact_history:
        db.delete(db_fact_history)
        db.commit()
    return db_fact_history


# --- Operaciones CRUD para ForecastSmoothingParameters ---
def get_forecast_smoothing_parameter(db: Session, forecast_run_id: uuid.UUID):
    return db.query(models.ForecastSmoothingParameter).filter(models.ForecastSmoothingParameter.forecast_run_id == forecast_run_id).first()

def get_forecast_smoothing_parameters(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ForecastSmoothingParameter).offset(skip).limit(limit).all()

def create_forecast_smoothing_parameter(db: Session, forecast_run_id: uuid.UUID, client_id: uuid.UUID, alpha: float, user_id: uuid.UUID):
    db_param = models.ForecastSmoothingParameter(
        forecast_run_id=forecast_run_id,
        client_id=client_id,
        alpha=alpha,
        user_id=user_id
    )
    db.add(db_param)
    db.commit()
    db.refresh(db_param)
    return db_param


# --- Operaciones CRUD para ForecastVersions ---
def get_forecast_version(db: Session, version_id: uuid.UUID):
    return db.query(models.ForecastVersion).filter(models.ForecastVersion.version_id == version_id).first()

def get_forecast_versions(db: Session, client_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[models.ForecastVersion]:
    query = db.query(models.ForecastVersion)
    if client_id:
        query = query.filter(models.ForecastVersion.client_id == client_id)
    return query.offset(skip).limit(limit).all()

def create_forecast_version(db: Session, version_data: schemas.ForecastVersionCreate, current_forecast_data_to_version: List[Dict[str, Any]]) -> models.ForecastVersion:
    new_version_id = uuid.uuid4()
    db_version = models.ForecastVersion(
        version_id=new_version_id,
        client_id=version_data.client_id,
        user_id=version_data.user_id,
        version_name=version_data.version_name,
        history_source_used=version_data.history_source_used,
        smoothing_parameter_used=version_data.smoothing_parameter_used,
        statistical_model_applied=version_data.statistical_model_applied,
        creation_date=datetime.now(),
        notes=version_data.notes
    )
    db.add(db_version)
    db.flush() 

    versioned_records = []
    for row in current_forecast_data_to_version:
        client_id = uuid.UUID(str(row["client_id"])) if not isinstance(row["client_id"], uuid.UUID) else row["client_id"]
        sku_id = uuid.UUID(str(row["sku_id"])) if not isinstance(row["sku_id"], uuid.UUID) else row["sku_id"]
        client_final_id = uuid.UUID(str(row["client_final_id"])) if not isinstance(row["client_final_id"], uuid.UUID) else row["client_final_id"]
        period = row["period"].date() if isinstance(row["period"], datetime) else row["period"]
        
        versioned_record = models.FactForecastVersioned(
            version_id=new_version_id,
            client_id=client_id,
            sku_id=sku_id,
            client_final_id=client_final_id,
            key_figure_id=row["key_figure_id"], 
            period=period,
            value=row["value"],
            user_id=version_data.user_id 
        )
        versioned_records.append(versioned_record)

    if versioned_records:
        db.bulk_save_objects(versioned_records)
    
    db.commit()
    db.refresh(db_version)
    return db_version


# --- Operaciones CRUD para FactForecastStat ---
def get_fact_forecast_stat(
    db: Session,
    client_id: uuid.UUID, sku_id: uuid.UUID, client_final_id: uuid.UUID, period: date
):
    return db.query(models.FactForecastStat).filter(
        models.FactForecastStat.client_id == client_id,
        models.FactForecastStat.sku_id == sku_id,
        models.FactForecastStat.client_final_id == client_final_id,
        models.FactForecastStat.period == period
    ).first()

def get_fact_forecast_stat_data(
    db: Session,
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    forecast_run_ids: Optional[List[uuid.UUID]] = None,
    key_figure_ids: Optional[List[int]] = None, # <--- AÑADIDO: key_figure_ids
    skip: int = 0,
    limit: int = 100
) -> List[models.FactForecastStat]:
    query = db.query(models.FactForecastStat).options(
        joinedload(models.FactForecastStat.client),
        joinedload(models.FactForecastStat.sku),
        joinedload(models.FactForecastStat.key_figure)
    )
    if client_ids:
        query = query.filter(models.FactForecastStat.client_id.in_(client_ids))
    if sku_ids:
        query = query.filter(models.FactForecastStat.sku_id.in_(sku_ids))
    if start_period:
        query = query.filter(models.FactForecastStat.period >= start_period)
    if end_period:
        query = query.filter(models.FactForecastStat.period <= end_period)
    if forecast_run_ids:
        query = query.filter(models.FactForecastStat.forecast_run_id.in_(forecast_run_ids))
    if key_figure_ids: # <--- AÑADIDO: Filtrar por key_figure_ids
        query = query.filter(models.FactForecastStat.key_figure_id.in_(key_figure_ids))

    return query.offset(skip).limit(limit).all()

def create_fact_forecast_stat_batch(db: Session, forecast_records: List[Dict[str, Any]]):
    """
    Inserta o actualiza un lote de registros de pronóstico estadístico.
    Utiliza ON CONFLICT DO UPDATE para manejar duplicados.
    """
    if not forecast_records:
        return 0

    conn = get_raw_connection(db)
    cursor = conn.cursor()

    query = """
        INSERT INTO fact_forecast_stat (client_id, sku_id, client_final_id, period, value, model_used, forecast_run_id, user_id, key_figure_id)
        VALUES %s
        ON CONFLICT (client_id, sku_id, client_final_id, period, key_figure_id) DO UPDATE
        SET
            value = EXCLUDED.value,
            model_used = EXCLUDED.model_used,
            forecast_run_id = EXCLUDED.forecast_run_id,
            created_at = CURRENT_TIMESTAMP,
            user_id = EXCLUDED.user_id;
    """

    values_to_insert = [
        (r['client_id'], r['sku_id'], r['client_final_id'], r['period'], r['value'],
         r['model_used'], r['forecast_run_id'], r['user_id'], r['key_figure_id'])
        for r in forecast_records
    ]

    try:
        extras.execute_values(
            cursor,
            query,
            values_to_insert
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

    return len(forecast_records)


# --- Operaciones CRUD para FactAdjustments (¡Importante!) ---
def get_fact_adjustments(
    db: Session,
    client_id: uuid.UUID, sku_id: uuid.UUID, client_final_id: uuid.UUID, period: date,
    key_figure_id: int, adjustment_type_id: int
):
    return db.query(models.FactAdjustments).filter(
        models.FactAdjustments.client_id == client_id,
        models.FactAdjustments.sku_id == sku_id,
        models.FactAdjustments.client_final_id == client_final_id,
        models.FactAdjustments.period == period,
        models.FactAdjustments.key_figure_id == key_figure_id,
        models.FactAdjustments.adjustment_type_id == adjustment_type_id
    ).first()

def get_fact_adjustments_data(
    db: Session,
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    key_figure_ids: Optional[List[int]] = None,
    adjustment_type_ids: Optional[List[int]] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.FactAdjustments]:
    query = db.query(models.FactAdjustments).options(
        joinedload(models.FactAdjustments.client),
        joinedload(models.FactAdjustments.sku),
        joinedload(models.FactAdjustments.key_figure),
        joinedload(models.FactAdjustments.adjustment_type)
    )
    if client_ids:
        query = query.filter(models.FactAdjustments.client_id.in_(client_ids))
    if sku_ids:
        query = query.filter(models.FactAdjustments.sku_id.in_(sku_ids))
    if start_period:
        query = query.filter(models.FactAdjustments.period >= start_period)
    if end_period:
        query = query.filter(models.FactAdjustments.period <= end_period)
    if key_figure_ids:
        query = query.filter(models.FactAdjustments.key_figure_id.in_(key_figure_ids))
    if adjustment_type_ids:
        query = query.filter(models.FactAdjustments.adjustment_type_id.in_(adjustment_type_ids))
    return query.offset(skip).limit(limit).all()

# Nueva función para obtener ajustes para cálculos específicos
def get_fact_adjustments_for_calculation(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    start_period: date,
    end_period: date,
    key_figure_id: Optional[int] = None,
    adjustment_type_ids: Optional[List[int]] = None
) -> List[models.FactAdjustments]:
    query = db.query(models.FactAdjustments).filter(
        models.FactAdjustments.client_id == client_id,
        models.FactAdjustments.sku_id == sku_id,
        models.FactAdjustments.period >= start_period,
        models.FactAdjustments.period <= end_period
    ).options(
        joinedload(models.FactAdjustments.client),
        joinedload(models.FactAdjustments.sku),
        joinedload(models.FactAdjustments.key_figure),
        joinedload(models.FactAdjustments.adjustment_type)
    )
    if key_figure_id:
        query = query.filter(models.FactAdjustments.key_figure_id == key_figure_id)
    if adjustment_type_ids:
        query = query.filter(models.FactAdjustments.adjustment_type_id.in_(adjustment_type_ids))
    return query.order_by(models.FactAdjustments.period).all()


def update_fact_adjustment(
    db: Session,
    client_id: uuid.UUID,
    sku_id: uuid.UUID,
    client_final_id: uuid.UUID,
    period: date,
    key_figure_id: int,
    adjustment_type_id: int,
    adjustment_update: schemas.FactAdjustmentsBase
):
    db_adjustment = get_fact_adjustments(db, client_id, sku_id, client_final_id, period, key_figure_id, adjustment_type_id)
    if db_adjustment:
        for key, value in adjustment_update.model_dump(exclude_unset=True).items():
            setattr(db_adjustment, key, value)
        db_adjustment.timestamp = func.now()
        db.commit()
        db.refresh(db_adjustment)
    return db_adjustment


def upsert_fact_adjustment(db: Session, adjustment: schemas.FactAdjustmentsCreate):
    existing_adjustment = get_fact_adjustments(
        db,
        client_id=adjustment.client_id,
        sku_id=adjustment.sku_id,
        client_final_id=adjustment.client_final_id,
        period=adjustment.period,
        key_figure_id=adjustment.key_figure_id,
        adjustment_type_id=adjustment.adjustment_type_id
    )

    if existing_adjustment:
        updated_adjustment = update_fact_adjustment(
            db,
            client_id=adjustment.client_id,
            sku_id=adjustment.sku_id,
            client_final_id=adjustment.client_final_id,
            period=adjustment.period,
            key_figure_id=adjustment.key_figure_id,
            adjustment_type_id=adjustment.adjustment_type_id,
            adjustment_update=adjustment
        )
        return updated_adjustment
    else:
        db_adjustment = models.FactAdjustments(
            client_id=adjustment.client_id,
            sku_id=adjustment.sku_id,
            client_final_id=adjustment.client_final_id,
            period=adjustment.period,
            key_figure_id=adjustment.key_figure_id,
            adjustment_type_id=adjustment.adjustment_type_id,
            value=adjustment.value,
            comment=adjustment.comment,
            user_id=adjustment.user_id
        )
        db.add(db_adjustment)
        db.commit()
        db.refresh(db_adjustment)
        return db_adjustment

# --- Operaciones CRUD para FactForecastVersioned (Básicas GET y CREATE) ---
def get_fact_forecast_versioned(
    db: Session,
    version_id: uuid.UUID,
    client_id: uuid.UUID, sku_id: uuid.UUID, client_final_id: uuid.UUID, period: date,
    key_figure_id: int
):
    return db.query(models.FactForecastVersioned).filter(
        models.FactForecastVersioned.version_id == version_id,
        models.FactForecastVersioned.client_id == client_id,
        models.FactForecastVersioned.sku_id == sku_id,
        models.FactForecastVersioned.client_final_id == client_final_id,
        models.FactForecastVersioned.period == period,
        models.FactForecastVersioned.key_figure_id == key_figure_id
    ).first()

def get_fact_forecast_versioned_data(
    db: Session,
    version_ids: Optional[List[uuid.UUID]] = None,
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    key_figure_ids: Optional[List[int]] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.FactForecastVersioned]:
    query = db.query(models.FactForecastVersioned).options(
        joinedload(models.FactForecastVersioned.version),
        joinedload(models.FactForecastVersioned.client),
        joinedload(models.FactForecastVersioned.sku),
        joinedload(models.FactForecastVersioned.key_figure)
    )
    if version_ids:
        query = query.filter(models.FactForecastVersioned.version_id.in_(version_ids))
    if client_ids:
        query = query.filter(models.FactForecastVersioned.client_id.in_(client_ids))
    if sku_ids:
        query = query.filter(models.FactForecastVersioned.sku_id.in_(sku_ids))
    if start_period:
        query = query.filter(models.FactForecastVersioned.period >= start_period)
    if end_period:
        query = query.filter(models.FactForecastVersioned.period <= end_period)
    if key_figure_ids:
        query = query.filter(models.FactForecastVersioned.key_figure_id.in_(key_figure_ids))
    return query.offset(skip).limit(limit).all()

# --- Operaciones CRUD para ManualInputComments (Básicas GET y CREATE) ---
def get_manual_input_comment(
    db: Session,
    client_id: uuid.UUID, sku_id: uuid.UUID, client_final_id: uuid.UUID, period: date, key_figure_id: int
):
    return db.query(models.ManualInputComment).filter(
        models.ManualInputComment.client_id == client_id,
        models.ManualInputComment.sku_id == sku_id,
        models.ManualInputComment.client_final_id == client_final_id,
        models.ManualInputComment.period == period,
        models.ManualInputComment.key_figure_id == key_figure_id
    ).first()

def get_manual_input_comment_data(
    db: Session,
    client_ids: Optional[List[uuid.UUID]] = None,
    sku_ids: Optional[List[uuid.UUID]] = None,
    start_period: Optional[date] = None,
    end_period: Optional[date] = None,
    key_figure_ids: Optional[List[int]] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.ManualInputComment]:
    query = db.query(models.ManualInputComment).options(
        joinedload(models.ManualInputComment.client),
        joinedload(models.ManualInputComment.sku),
        joinedload(models.ManualInputComment.key_figure)
    )
    if client_ids:
        query = query.filter(models.ManualInputComment.client_id.in_(client_ids))
    if sku_ids:
        query = query.filter(models.ManualInputComment.sku_id.in_(sku_ids))
    if start_period:
        query = query.filter(models.ManualInputComment.period >= start_period)
    if end_period:
        query = query.filter(models.ManualInputComment.period <= end_period)
    if key_figure_ids:
        query = query.filter(models.ManualInputComment.key_figure_id.in_(key_figure_ids))
    return query.order_by(models.ManualInputComment.created_at.desc()).offset(skip).limit(limit).all()


def create_manual_input_comment(db: Session, comment: schemas.ManualInputCommentCreate):
    db_comment = models.ManualInputComment(
        client_id=comment.client_id,
        sku_id=comment.sku_id,
        client_final_id=comment.client_final_id,
        period=comment.period,
        key_figure_id=comment.key_figure_id,
        comment=comment.comment,
        user_id=comment.user_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment