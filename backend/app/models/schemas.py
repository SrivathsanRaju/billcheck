from datetime import datetime
from typing import Optional, Any, List, Dict
from pydantic import BaseModel


class InvoiceData(BaseModel):
    awb_number: str
    shipment_date: Optional[str] = None
    origin_pincode: Optional[str] = None
    destination_pincode: Optional[str] = None
    weight_billed: Optional[float] = None
    zone: Optional[str] = None
    base_freight: Optional[float] = None
    cod_fee: Optional[float] = None
    rto_fee: Optional[float] = None
    fuel_surcharge: Optional[float] = None
    other_surcharges: Optional[float] = None
    gst_rate: Optional[float] = 18.0
    total_billed: Optional[float] = None


class ContractData(BaseModel):
    provider: Optional[str] = None
    # weight_slabs as plain dicts: {zone, min, max, base_rate, per_extra_kg}
    weight_slabs: List[Dict[str, Any]] = []
    cod_rate: Optional[float] = 1.5
    cod_rate_type: str = "percentage"
    rto_rate: Optional[float] = 50.0
    fuel_surcharge_pct: Optional[float] = 12.0
    gst_pct: float = 18.0
    raw_data: Optional[Dict[str, Any]] = None


class DiscrepancyResult(BaseModel):
    check_type: str
    severity: str
    description: str
    billed_value: Optional[float] = None
    expected_value: Optional[float] = None
    overcharge_amount: float = 0.0
    confidence_score: float = 0.8
    confidence_reason: Optional[str] = None
    awb_number: Optional[str] = None


class BatchSummary(BaseModel):
    id: int
    invoice_file: str
    contract_file: str
    provider_name: str
    status: str
    total_invoices: int
    processed_invoices: int
    error_message: Optional[str] = None
    summary: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DiscrepancyOut(BaseModel):
    id: int
    invoice_id: int
    batch_id: int
    awb_number: str
    check_type: str
    description: str
    billed_value: Optional[float] = None
    expected_value: Optional[float] = None
    overcharge_amount: float
    severity: str
    confidence_score: float
    confidence_reason: Optional[str] = None
    dispute_status: str
    dispute_notes: Optional[str] = None
    dispute_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisputeUpdate(BaseModel):
    dispute_status: str
    dispute_notes: Optional[str] = None


class AlertOut(BaseModel):
    id: int
    batch_id: Optional[int] = None
    provider_name: Optional[str] = None
    alert_type: str
    title: str
    message: str
    severity: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ContractOut(BaseModel):
    id: int
    name: str
    provider: str
    file_path: Optional[str] = None
    extracted_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
