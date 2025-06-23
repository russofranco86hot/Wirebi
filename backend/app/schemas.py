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
    key_figure_id: int # Permitir que el ID sea especificado para KeyFigures fijas como Sales/Order

class DimKeyFigure(DimKeyFigureBase):
    key_figure_id: int

    class Config:
        from_attributes = True # Reemplaza orm_mode = True en Pydantic v2+

class DimClientBase(BaseModel):
    client_name: str

class DimClientCreate(DimClientBase):
    pass # Por ahora, solo el nombre es necesario para crear un cliente

class DimClient(DimClientBase):
    client_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DimSkuBase(BaseModel):
    sku_name: str

class DimSkuCreate(DimSkuBase):
    pass # Por ahora, solo el nombre es necesario para crear un SKU

class DimSku(DimSkuBase):
    sku_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Esquemas para Tablas de Hechos ---

# FactHistory: Representa una fila de datos históricos de ventas
class FactHistoryBase(BaseModel):
    client_id: uuid.UUID
    sku_id: uuid.UUID
    client_final_id: uuid.UUID # Asumiendo que es un UUID generado, no un FK directo a una dimensión
    period: date
    source: str # Debería ser 'sales' o 'shipments'
    key_figure_id: int
    value: Optional[float] = None

class FactHistoryCreate(FactHistoryBase):
    # Cuando creas un registro, quizás no necesites todos los campos de metadata
    # user_id puede ser opcional al crear y asignado por el backend
    pass 

class FactHistory(FactHistoryBase):
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Opcional: Incluir la relación con las dimensiones para el GET
    # Para el Pydantic Schema, esto es lo que se "unirá"
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure

    class Config:
        from_attributes = True


# FactForecastVersioned: Representa una fila de pronóstico versionado
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
    # Opcional: Incluir la relación con las dimensiones
    version: Optional["ForecastVersion"] = None # Forward reference, see below
    client: DimClient
    sku: DimSku
    key_figure: DimKeyFigure

    class Config:
        from_attributes = True


# Esquemas para Tablas Auxiliares (si se exponen vía API)
class ForecastSmoothingParameterBase(BaseModel):
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

class ForecastVersionBase(BaseModel):
    client_id: uuid.UUID
    name: str
    created_by: Optional[uuid.UUID] = None
    history_source: str
    model_used: Optional[str] = None
    forecast_run_id: Optional[uuid.UUID] = None # Puede ser nulo si la versión no tiene un run asociado
    notes: Optional[str] = None

class ForecastVersionCreate(ForecastVersionBase):
    pass

class ForecastVersion(ForecastVersionBase):
    version_id: uuid.UUID
    created_at: datetime
    
    client: DimClient # Relación con DimClient
    # forecast_run: Optional[ForecastSmoothingParameter] = None # Relación opcional, evitar circularidad si no es estrictamente necesario en el output

    class Config:
        from_attributes = True

# Actualizar forward references si es necesario
# FactForecastVersioned.update_forward_refs() # No es necesario en Pydantic V2 con from_attributes=True
# Si ves errores de "NameError: name 'ForecastVersion' is not defined", puedes descomentar la línea anterior
# si usas Pydantic v1, o asegurar que ForecastVersion esté definido antes.