# backend/app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any 
from datetime import date, datetime
import uuid

# --- Constantes para Key Figures (¡AHORA DEFINITIVAS Y CANÓNICAS!)
KEY_FIGURE_SALES_ID = 1
KEY_FIGURE_SMOOTHED_SALES_ID = 2
KEY_FIGURE_ORDERS_ID = 3
KEY_FIGURE_SMOOTHED_ORDERS_ID = 4
KEY_FIGURE_MANUAL_INPUT_ID = 5
KEY_FIGURE_STAT_FORECAST_SALES_ID = 6
KEY_FIGURE_STAT_FORECAST_ORDERS_ID = 7
KEY_FIGURE_FINAL_FORECAST_ID = 8

# No hay necesidad de IDs para ajuste por cantidad/porcentaje/override como Key Figures,
# porque son tipos de ajuste que se aplican a las Key Figures principales.
# KEY_FIGURE_OVERRIDE_ID = 10 (removido, Override es un tipo de ajuste sobre una KF existente)

# --- Constantes para Adjustment Types (debe coincidir con los IDs de tu base de datos)
ADJUSTMENT_TYPE_QTY_ID = 1
ADJUSTMENT_TYPE_PCT_ID = 2
ADJUSTMENT_TYPE_OVERRIDE_ID = 3


# --- Esquemas para Tablas Dimensiones ---

class DimKeyFigureBase(BaseModel):
    name: str
    applies_to: Optional[str] = None
    editable: bool = True
    order: Optional[int] = None

class DimKeyFigureCreate(DimKeyFigureBase):
    key_figure_id: int

class DimKeyFigure(DimKeyFigureBase):
    key_figure_id: int

    class Config:
        from_attributes = True

class DimClientBase(BaseModel):
    client_name: str

class DimClientCreate(DimClientBase):
    pass

class DimClient(DimClientBase):
    client_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DimSkuBase(BaseModel):
    sku_name: str

class DimSkuCreate(DimSkuBase):
    pass

class DimSku(DimSkuBase):
    sku_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DimAdjustmentTypeBase(BaseModel):
    name: str

class DimAdjustmentTypeCreate(DimAdjustmentTypeBase):
    adjustment_type_id: int

class DimAdjustmentType(DimAdjustmentTypeBase):
    adjustment_type_id: int

    class Config:
        from_attributes = True

# --- Esquemas para Tablas de Hechos (Facts) ---

class FactHistoryBase(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    source: str 
    key_figure_id: int
    value: Optional[float] = None
    user_id: Optional[uuid.UUID] = None

class FactHistoryCreate(FactHistoryBase):
    pass

class FactHistory(FactHistoryBase):
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: Optional[uuid.UUID] = None
    client: Optional[DimClient] = None
    sku: Optional[DimSku] = None
    key_figure: Optional[DimKeyFigure] = None

    class Config:
        from_attributes = True


class ForecastSmoothingParameterBase(BaseModel):
    forecast_run_id: uuid.UUID
    client_id: uuid.UUID
    alpha: float

class ForecastSmoothingParameterCreate(ForecastSmoothingParameterBase):
    pass

class ForecastSmoothingParameter(ForecastSmoothingParameterBase):
    created_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True


# --- ESQUEMAS PARA VERSIONADO (SNAPSHOTS) ---
class ForecastVersionCreate(BaseModel):
    client_id: uuid.UUID
    user_id: uuid.UUID
    version_name: str
    history_source_used: str
    smoothing_parameter_used: Optional[float] = None
    statistical_model_applied: Optional[str] = None
    notes: Optional[str] = None

class ForecastVersion(BaseModel):
    version_id: uuid.UUID
    client_id: uuid.UUID
    user_id: uuid.UUID
    version_name: str
    history_source_used: str
    smoothing_parameter_used: Optional[float] = None
    statistical_model_applied: Optional[str] = None
    creation_date: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class FactForecastStatBase(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    model_used: Optional[str] = None
    forecast_run_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None

class FactForecastStatCreate(FactForecastStatBase):
    pass

class FactForecastStat(FactForecastStatBase):
    created_at: datetime
    user_id: Optional[uuid.UUID] = None
    client: DimClient
    sku: DimSku
    forecast_run: Optional[ForecastSmoothingParameter]

    class Config:
        from_attributes = True

class FactAdjustmentsBase(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    key_figure_id: int
    adjustment_type_id: int
    value: Optional[float] = None
    comment: Optional[str] = None
    user_id: Optional[uuid.UUID] = None

class FactAdjustmentsCreate(FactAdjustmentsBase):
    pass

class FactAdjustments(FactAdjustmentsBase):
    timestamp: datetime
    user_id: Optional[uuid.UUID] = None
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure
    adjustment_type: DimAdjustmentType

    class Config:
        from_attributes = True

class FactForecastVersionedBase(BaseModel):
    version_id: uuid.UUID
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    key_figure_id: int
    value: Optional[float] = None
    user_id: Optional[uuid.UUID] = None

class FactForecastVersionedCreate(FactForecastVersionedBase):
    pass

class FactForecastVersioned(FactForecastVersionedBase):
    version: Optional[ForecastVersion]
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure
    user_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

class ManualInputCommentBase(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    key_figure_id: int
    comment: Optional[str] = None
    user_id: Optional[uuid.UUID] = None

class ManualInputCommentCreate(ManualInputCommentBase):
    pass

class ManualInputComment(ManualInputCommentBase):
    created_at: datetime
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure
    user_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

# Estos esquemas ahora representarán directamente las nuevas 8 Key Figures
class CleanHistoryData(BaseModel): # Esto ahora se mapearía a "Manual input" (ID 5)
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    clientName: Optional[str] = None
    skuName: Optional[str] = None
    # keyFigureName: Optional[str] = "Historia Limpia" # Remover si ya no existe


    class Config:
        from_attributes = True

class FinalForecastData(BaseModel): # Esto se mapearía a "Final Forecast" (ID 8)
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    clientName: Optional[str] = None
    skuName: Optional[str] = None
    # keyFigureName: Optional[str] = "Pronóstico Final" # Remover si ya no existe

    class Config:
        from_attributes = True