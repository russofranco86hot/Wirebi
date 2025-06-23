from sqlalchemy import Column, Integer, Text, Boolean, Date, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .database import Base

# Definir los ENUMs fuera de las clases para reusabilidad si son usados en múltiples tablas
source_enum = ENUM('shipments', 'sales', name='source', create_type=False)

# --- Tablas Dimensioanles ---
class DimKeyFigure(Base):
    __tablename__ = "dim_keyfigures"
    key_figure_id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False, unique=True)
    applies_to = Column(Text)
    editable = Column(Boolean, default=True)
    order = Column(Integer)

class DimClient(Base):
    __tablename__ = "dim_clients"
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class DimSku(Base):
    __tablename__ = "dim_skus"
    sku_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_name = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# --- Tablas Auxiliares ---
class ForecastSmoothingParameter(Base):
    __tablename__ = "forecast_smoothing_parameters"
    forecast_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    alpha = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(UUID(as_uuid=True))

    client = relationship("DimClient") # Relación con DimClient

class ForecastVersion(Base):
    __tablename__ = "forecast_versions"
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(UUID(as_uuid=True))
    history_source = Column(source_enum)
    model_used = Column(Text)
    forecast_run_id = Column(UUID(as_uuid=True), ForeignKey("forecast_smoothing_parameters.forecast_run_id"))
    notes = Column(Text)

    client = relationship("DimClient") # Relación con DimClient
    forecast_run = relationship("ForecastSmoothingParameter") # Relación con ForecastSmoothingParameter

# --- Tablas de Hechos ---
class FactHistory(Base):
    __tablename__ = "fact_history"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), primary_key=True)
    client_final_id = Column(UUID(as_uuid=True), primary_key=True) # Assuming this is a generated ID, not FK to another dim
    period = Column(Date, primary_key=True)
    source = Column(source_enum)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), primary_key=True)
    value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    user_id = Column(UUID(as_uuid=True))

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")

class FactForecastStat(Base):
    __tablename__ = "fact_forecast_stat"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), primary_key=True)
    client_final_id = Column(UUID(as_uuid=True), primary_key=True)
    period = Column(Date, primary_key=True)
    value = Column(Float)
    model_used = Column(Text)
    forecast_run_id = Column(UUID(as_uuid=True), ForeignKey("forecast_smoothing_parameters.forecast_run_id"))
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(UUID(as_uuid=True))

    client = relationship("DimClient")
    sku = relationship("DimSku")
    forecast_run = relationship("ForecastSmoothingParameter")

class FactAdjustments(Base):
    __tablename__ = "fact_adjustments"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), primary_key=True)
    client_final_id = Column(UUID(as_uuid=True), primary_key=True)
    period = Column(Date, primary_key=True)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), primary_key=True)
    adjustment_type_id = Column(Integer, primary_key=True) # Assuming no FK for adjustment_type_id yet
    value = Column(Float)
    comment = Column(Text)
    user_id = Column(UUID(as_uuid=True))
    timestamp = Column(DateTime, server_default=func.now())

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")

class FactForecastVersioned(Base):
    __tablename__ = "fact_forecast_versioned"
    version_id = Column(UUID(as_uuid=True), ForeignKey("forecast_versions.version_id"), primary_key=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), primary_key=True)
    client_final_id = Column(UUID(as_uuid=True), primary_key=True)
    period = Column(Date, primary_key=True)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), primary_key=True)
    value = Column(Float)

    version = relationship("ForecastVersion")
    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")

class ManualInputComment(Base):
    __tablename__ = "manual_input_comments"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), primary_key=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), primary_key=True)
    client_final_id = Column(UUID(as_uuid=True), primary_key=True)
    period = Column(Date, primary_key=True)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), primary_key=True)
    comment = Column(Text)
    user_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")