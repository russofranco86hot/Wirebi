# backend/app/models.py

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, TIMESTAMP, Boolean 
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint 
import uuid

Base = declarative_base()

# DIMENSIONAL TABLES
class DimKeyFigure(Base):
    __tablename__ = "dim_keyfigures"
    key_figure_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    applies_to = Column(String) 
    editable = Column(Boolean, default=True)
    order = Column(Integer) 

class DimAdjustmentType(Base):
    __tablename__ = "dim_adjustment_types"
    adjustment_type_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class DimClient(Base):
    __tablename__ = "dim_clients"
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(String, nullable=False, unique=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class DimSku(Base):
    __tablename__ = "dim_skus"
    sku_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_name = Column(String, nullable=False, unique=True) 
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

# AUXILIARY TABLES
class ForecastSmoothingParameter(Base):
    __tablename__ = "forecast_smoothing_parameters"
    forecast_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    alpha = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    user_id = Column(UUID(as_uuid=True)) 

    client = relationship("DimClient") 

class ForecastVersion(Base): 
    __tablename__ = "forecast_versions"
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    
    version_name = Column("name", String, nullable=False) 
    user_id = Column("created_by", UUID(as_uuid=True), nullable=False) 
    history_source_used = Column("history_source", String, nullable=False) 
    creation_date = Column("created_at", TIMESTAMP(timezone=True), default=func.now())

    model_used = Column(String, nullable=True)
    forecast_run_id = Column(UUID(as_uuid=True), ForeignKey("forecast_smoothing_parameters.forecast_run_id"), nullable=True)
    notes = Column(String, nullable=True)

    client = relationship("DimClient", backref="forecast_versions")
    forecast_run = relationship("ForecastSmoothingParameter")


# FACT TABLES
class FactHistory(Base):
    __tablename__ = "fact_history"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), nullable=False)
    client_final_id = Column(UUID(as_uuid=True), nullable=False) 
    period = Column(Date, nullable=False)
    source = Column(String, nullable=False) 
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), nullable=False)
    value = Column(Float)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    user_id = Column(UUID(as_uuid=True))

    __table_args__ = (
        PrimaryKeyConstraint("client_id", "sku_id", "client_final_id", "period", "key_figure_id", "source"),
    )

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")


class FactForecastStat(Base):
    __tablename__ = "fact_forecast_stat"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), nullable=False)
    client_final_id = Column(UUID(as_uuid=True), nullable=False)
    period = Column(Date, nullable=False)
    value = Column(Float)
    model_used = Column(String)
    forecast_run_id = Column(UUID(as_uuid=True), ForeignKey("forecast_smoothing_parameters.forecast_run_id"))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    user_id = Column(UUID(as_uuid=True))
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), nullable=False) # <-- ¡AÑADIDA ESTA COLUMNA!

    __table_args__ = (
        PrimaryKeyConstraint("client_id", "sku_id", "client_final_id", "period", "key_figure_id"), # <-- ¡key_figure_id añadido a PK!
    )

    client = relationship("DimClient")
    sku = relationship("DimSku")
    forecast_run = relationship("ForecastSmoothingParameter")
    key_figure = relationship("DimKeyFigure") # <-- Añadida relación a DimKeyFigure


class FactAdjustments(Base):
    __tablename__ = "fact_adjustments"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), nullable=False)
    client_final_id = Column(UUID(as_uuid=True), nullable=False)
    period = Column(Date, nullable=False)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), nullable=False)
    adjustment_type_id = Column(Integer, ForeignKey("dim_adjustment_types.adjustment_type_id"), nullable=False)
    value = Column(Float)
    comment = Column(String)
    user_id = Column(UUID(as_uuid=True))
    timestamp = Column(TIMESTAMP(timezone=True), default=func.now()) 

    __table_args__ = (
        PrimaryKeyConstraint("client_id", "sku_id", "client_final_id", "period", "key_figure_id"),
    )

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")
    adjustment_type = relationship("DimAdjustmentType")


class FactForecastVersioned(Base):
    __tablename__ = "fact_forecast_versioned"
    version_id = Column(UUID(as_uuid=True), ForeignKey("forecast_versions.version_id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), nullable=False)
    client_final_id = Column(UUID(as_uuid=True), nullable=False)
    period = Column(Date, nullable=False)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), nullable=False)
    value = Column(Float)
    
    __table_args__ = (
        PrimaryKeyConstraint("version_id", "client_id", "sku_id", "client_final_id", "period", "key_figure_id"),
    )

    version = relationship("ForecastVersion")
    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")


class ManualInputComment(Base):
    __tablename__ = "manual_input_comments"
    client_id = Column(UUID(as_uuid=True), ForeignKey("dim_clients.client_id"), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("dim_skus.sku_id"), nullable=False)
    client_final_id = Column(UUID(as_uuid=True), nullable=False)
    period = Column(Date, nullable=False)
    key_figure_id = Column(Integer, ForeignKey("dim_keyfigures.key_figure_id"), nullable=False)
    comment = Column(String)
    user_id = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("client_id", "sku_id", "client_final_id", "period", "key_figure_id"),
    )

    client = relationship("DimClient")
    sku = relationship("DimSku")
    key_figure = relationship("DimKeyFigure")