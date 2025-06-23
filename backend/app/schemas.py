# backend/app/schemas.py - Versión corregida para forecaist_schema.sql

from pydantic import BaseModel
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

class DimAdjustmentTypeBase(BaseModel): # De forecaist_schema.sql
    name: str

class DimAdjustmentTypeCreate(DimAdjustmentTypeBase):
    adjustment_type_id: int

class DimAdjustmentType(DimAdjustmentTypeBase):
    adjustment_type_id: int

    class Config:
        from_attributes = True

# --- Esquemas para Tablas Auxiliares ---

class ForecastSmoothingParameterBase(BaseModel): # De forecaist_schema.sql
    client_id: uuid.UUID
    alpha: float
    user_id: Optional[uuid.UUID] = None

class ForecastSmoothingParameterCreate(ForecastSmoothingParameterBase):
    pass

class ForecastSmoothingParameter(ForecastSmoothingParameterBase):
    forecast_run_id: uuid.UUID
    created_at: datetime
    client: DimClient # Relación

    class Config:
        from_attributes = True

class ForecastVersionBase(BaseModel): # De forecaist_schema.sql
    client_id: uuid.UUID
    name: str
    created_by: Optional[uuid.UUID] = None
    history_source: Optional[str] = None
    model_used: Optional[str] = None
    forecast_run_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

class ForecastVersionCreate(ForecastVersionBase):
    pass

class ForecastVersion(ForecastVersionBase):
    version_id: uuid.UUID
    created_at: datetime
    client: DimClient # Relación con DimClient
    # forecast_run: Optional[ForecastSmoothingParameter] # Evitar circularidad si no es esencial

    class Config:
        from_attributes = True


# --- Esquemas para Tablas de Hechos ---

class FactHistoryBase(BaseModel): # Actualizado para source en PK
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    source: str # Ahora puede ser 'sales' u 'order'
    key_figure_id: int
    value: Optional[float] = None

class FactHistoryCreate(FactHistoryBase):
    pass 

class FactHistory(FactHistoryBase):
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure

    class Config:
        from_attributes = True

class FactForecastStatBase(BaseModel): # De forecaist_schema.sql
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID
    period: date
    value: Optional[float] = None
    model_used: Optional[str] = None
    forecast_run_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

class FactForecastStatCreate(FactForecastStatBase):
    pass

class FactForecastStat(FactForecastStatBase):
    created_at: datetime
    client: DimClient
    sku: DimSku
    forecast_run: Optional[ForecastSmoothingParameter]

    class Config:
        from_attributes = True

class FactAdjustmentsBase(BaseModel): # De forecaist_schema.sql
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
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure
    adjustment_type: DimAdjustmentType

    class Config:
        from_attributes = True

class FactForecastVersionedBase(BaseModel): # De forecaist_schema.sql
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

class ManualInputCommentBase(BaseModel): # De forecaist_schema.sql
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