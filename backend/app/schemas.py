# backend/app/schemas.py - Versión corregida y completa para forecaist_schema.sql (con TIMESTAMP de FactHistory corregido)

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import uuid

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
    source: str # 'sales', 'order', 'shipments'
    key_figure_id: int
    value: Optional[float] = None

class FactHistoryCreate(FactHistoryBase):
    pass

class FactHistory(FactHistoryBase):
    # 'timestamp' ha sido reemplazado por 'created_at' y 'updated_at' para coincidir con la DB y models.py
    created_at: datetime
    updated_at: Optional[datetime] = None # updated_at puede ser nulo si el registro nunca se actualizó
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


class ForecastVersionBase(BaseModel):
    client_id: uuid.UUID
    name: str
    history_source: str
    model_used: str
    forecast_run_id: uuid.UUID # ID del run que generó esta versión
    notes: Optional[str] = None

class ForecastVersionCreate(ForecastVersionBase):
    pass

class ForecastVersion(ForecastVersionBase):
    version_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime
    created_by: uuid.UUID
    
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

class FactForecastStatCreate(FactForecastStatBase):
    pass

class FactForecastStat(FactForecastStatBase):
    created_at: datetime
    user_id: uuid.UUID
    client: DimClient
    sku: DimSku
    forecast_run: Optional[ForecastSmoothingParameter] # Relación opcional

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
    timestamp: datetime # Este campo sí está en el modelo y la DB para ajustes
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

class FactForecastVersionedCreate(FactForecastVersionedBase):
    pass

class FactForecastVersioned(FactForecastVersionedBase):
    version: Optional[ForecastVersion] # Relación a ForecastVersion
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure

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

    class Config:
        from_attributes = True

# --- Nuevos esquemas para Historia Limpia y Pronóstico Final ---
class CleanHistoryData(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    # Puedes añadir más campos si los necesitas, como el nombre del cliente/sku para el frontend
    clientName: Optional[str] = None
    skuName: Optional[str] = None
    keyFigureName: Optional[str] = "Historia Limpia" # Nombre fijo para este tipo de dato

    class Config:
        from_attributes = True

class FinalForecastData(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    # Puedes añadir más campos si los necesitas
    clientName: Optional[str] = None
    skuName: Optional[str] = None
    keyFigureName: Optional[str] = "Pronóstico Final" # Nombre fijo para este tipo de dato

    class Config:
        from_attributes = True