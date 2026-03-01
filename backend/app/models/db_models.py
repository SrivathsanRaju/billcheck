from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProcessingBatch(Base):
    __tablename__ = "processing_batches"
    id = Column(Integer, primary_key=True, index=True)
    invoice_file = Column(String)
    contract_file = Column(String)
    provider_name = Column(String, default="Unknown")
    status = Column(String, default="pending")  # pending/processing/completed/failed
    total_invoices = Column(Integer, default=0)
    processed_invoices = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="batch", cascade="all, delete-orphan")
    discrepancies = relationship("Discrepancy", back_populates="batch", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="batch", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("processing_batches.id"))
    awb_number = Column(String, index=True)
    shipment_date = Column(String, nullable=True)
    origin_pincode = Column(String, nullable=True)
    destination_pincode = Column(String, nullable=True)
    weight_billed = Column(Float, nullable=True)
    actual_weight = Column(Float, nullable=True)  # actual measured weight from invoice
    zone = Column(String, nullable=True)
    base_freight = Column(Float, default=0.0)
    cod_fee = Column(Float, nullable=True, default=None)
    rto_fee = Column(Float, nullable=True, default=None)
    fuel_surcharge = Column(Float, nullable=True, default=None)
    other_surcharges = Column(Float, nullable=True, default=None)
    gst_rate = Column(Float, default=18.0)
    total_billed = Column(Float, default=0.0)
    raw_extracted = Column(JSON, nullable=True)

    batch = relationship("ProcessingBatch", back_populates="invoices")
    discrepancies = relationship("Discrepancy", back_populates="invoice", cascade="all, delete-orphan")


class Discrepancy(Base):
    __tablename__ = "discrepancies"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    batch_id = Column(Integer, ForeignKey("processing_batches.id"))
    awb_number = Column(String)
    check_type = Column(String)
    description = Column(Text)
    billed_value = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    overcharge_amount = Column(Float, default=0.0)
    severity = Column(String, default="medium")  # critical/high/medium/low
    confidence_score = Column(Float, default=0.8)
    confidence_reason = Column(Text, nullable=True)
    dispute_status = Column(String, default="pending")  # pending/raised/acknowledged/resolved/rejected
    dispute_notes = Column(Text, nullable=True)
    dispute_updated_at = Column(DateTime, nullable=True)

    invoice = relationship("Invoice", back_populates="discrepancies")
    batch = relationship("ProcessingBatch", back_populates="discrepancies")


class SavedContract(Base):
    __tablename__ = "saved_contracts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    provider = Column(String)
    file_path = Column(String, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("processing_batches.id"), nullable=True)
    provider_name = Column(String, nullable=True)
    alert_type = Column(String)
    title = Column(String)
    message = Column(Text)
    severity = Column(String, default="medium")
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("ProcessingBatch", back_populates="alerts")
