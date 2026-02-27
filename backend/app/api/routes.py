import os
import shutil
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException, Form
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import io

from app.core.database import get_db
from app.core.config import settings
from app.models.db_models import ProcessingBatch, Invoice, Discrepancy, SavedContract, Alert
from app.models.schemas import BatchSummary, DiscrepancyOut, DisputeUpdate, AlertOut, ContractOut
from app.services.processor import process_batch
from app.services.dispute_letter import generate_dispute_letter
from app.services.csv_generator import generate_discrepancy_csv, generate_summary_csv, generate_payout_csv
from app.services.analytics import build_analytics

router = APIRouter(prefix="/api/v1")


def upload_file_path(filename: str) -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return os.path.join(settings.UPLOAD_DIR, filename)


@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    invoice_file: UploadFile = File(...),
    contract_file: Optional[UploadFile] = File(None),
    saved_contract_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not contract_file and not saved_contract_id:
        raise HTTPException(status_code=400, detail="Either contract_file or saved_contract_id is required.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    # Save invoice
    inv_path = os.path.join(settings.UPLOAD_DIR, f"{ts}_{invoice_file.filename}")
    with open(inv_path, "wb") as f:
        shutil.copyfileobj(invoice_file.file, f)

    # Resolve contract path
    if contract_file:
        con_path = os.path.join(settings.UPLOAD_DIR, f"{ts}_{contract_file.filename}")
        con_name = contract_file.filename
        with open(con_path, "wb") as f:
            shutil.copyfileobj(contract_file.file, f)
    else:
        # Load saved contract
        result = await db.execute(select(SavedContract).where(SavedContract.id == saved_contract_id))
        saved = result.scalar_one_or_none()
        if not saved:
            raise HTTPException(status_code=404, detail=f"Saved contract #{saved_contract_id} not found.")
        con_path = saved.file_path
        con_name = saved.name

    batch = ProcessingBatch(
        invoice_file=invoice_file.filename,
        contract_file=con_name,
        status="pending",
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    from app.core.database import AsyncSessionLocal
    async def run_in_bg():
        async with AsyncSessionLocal() as bg_db:
            await process_batch(batch.id, inv_path, con_path, bg_db)

    background_tasks.add_task(run_in_bg)
    return {"batch_id": batch.id, "status": "pending"}


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return {
        "id": batch.id,
        "status": batch.status,
        "provider_name": batch.provider_name,
        "total_invoices": batch.total_invoices,
        "processed_invoices": batch.processed_invoices,
        "error_message": batch.error_message,
        "summary": batch.summary,
        "invoice_file": batch.invoice_file,
        "contract_file": batch.contract_file,
        "created_at": batch.created_at.isoformat(),
    }


@router.get("/batch/{batch_id}/report")
async def get_batch_report(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Discrepancy).where(Discrepancy.batch_id == batch_id))
    discrepancies = result.scalars().all()
    return {"batch_id": batch_id, "discrepancies": [DiscrepancyOut.from_orm(d) for d in discrepancies]}


@router.get("/batch/{batch_id}/dispute-letter")
async def get_dispute_letter(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    result2 = await db.execute(select(Discrepancy).where(Discrepancy.batch_id == batch_id))
    discrepancies = result2.scalars().all()
    letter = generate_dispute_letter(batch, discrepancies, batch.provider_name)
    return PlainTextResponse(
        content=letter,
        headers={"Content-Disposition": f'attachment; filename="dispute_letter_batch_{batch_id}.txt"'},
    )


@router.get("/batch/{batch_id}/download/{dl_type}")
async def download_csv(batch_id: int, dl_type: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404)

    result_d = await db.execute(select(Discrepancy).where(Discrepancy.batch_id == batch_id))
    discrepancies = result_d.scalars().all()

    if dl_type == "discrepancy":
        content = generate_discrepancy_csv(discrepancies)
        filename = f"discrepancies_batch_{batch_id}.csv"
    elif dl_type == "summary":
        content = generate_summary_csv(batch, discrepancies)
        filename = f"summary_batch_{batch_id}.csv"
    elif dl_type == "payout":
        result_i = await db.execute(select(Invoice).where(Invoice.batch_id == batch_id))
        invoices = result_i.scalars().all()
        content = generate_payout_csv(invoices, discrepancies)
        filename = f"payout_batch_{batch_id}.csv"
    else:
        raise HTTPException(400, "Invalid type")

    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/batch/{batch_id}/disputes")
async def get_batch_disputes(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Discrepancy).where(Discrepancy.batch_id == batch_id))
    discs = result.scalars().all()
    return [DiscrepancyOut.from_orm(d) for d in discs]


@router.patch("/discrepancy/{disc_id}/dispute")
async def update_dispute(disc_id: int, payload: DisputeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Discrepancy).where(Discrepancy.id == disc_id))
    disc = result.scalar_one_or_none()
    if not disc:
        raise HTTPException(404)
    disc.dispute_status = payload.dispute_status
    disc.dispute_notes = payload.dispute_notes
    disc.dispute_updated_at = datetime.utcnow()
    await db.commit()
    return DiscrepancyOut.from_orm(disc)


@router.patch("/batch/{batch_id}/disputes/bulk")
async def bulk_raise_disputes(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Discrepancy).where(Discrepancy.batch_id == batch_id, Discrepancy.dispute_status == "pending")
    )
    discs = result.scalars().all()
    for d in discs:
        d.dispute_status = "raised"
        d.dispute_updated_at = datetime.utcnow()
    await db.commit()
    return {"raised": len(discs)}


@router.delete("/batch/{batch_id}")
async def delete_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404)
    await db.delete(batch)
    await db.commit()
    return {"deleted": batch_id}


@router.get("/batches")
async def list_batches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcessingBatch).order_by(ProcessingBatch.created_at.desc()).limit(50)
    )
    batches = result.scalars().all()
    return [
        {
            "id": b.id,
            "invoice_file": b.invoice_file,
            "contract_file": b.contract_file,
            "provider_name": b.provider_name,
            "status": b.status,
            "total_invoices": b.total_invoices,
            "processed_invoices": b.processed_invoices,
            "summary": b.summary,
            "created_at": b.created_at.isoformat(),
        }
        for b in batches
    ]


@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcessingBatch).where(ProcessingBatch.status == "completed").order_by(ProcessingBatch.created_at)
    )
    batches = result.scalars().all()
    result_d = await db.execute(select(Discrepancy))
    discrepancies = result_d.scalars().all()
    return build_analytics(batches, discrepancies)


@router.post("/contracts/save")
async def save_contract(
    name: str = Form(...),
    provider: str = Form(...),
    contract_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    from app.services.csv_fast_extractor import parse_contract_csv
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    path = os.path.join(settings.UPLOAD_DIR, f"contract_{ts}_{contract_file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(contract_file.file, f)
    content = open(path).read()
    extracted = parse_contract_csv(content)
    contract = SavedContract(name=name, provider=provider, file_path=path, extracted_data=extracted)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return ContractOut.from_orm(contract)


@router.get("/contracts")
async def list_contracts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedContract).order_by(SavedContract.created_at.desc()))
    return [ContractOut.from_orm(c) for c in result.scalars().all()]


@router.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedContract).where(SavedContract.id == contract_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404)
    await db.delete(c)
    await db.commit()
    return {"deleted": contract_id}


@router.get("/alerts")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).order_by(Alert.created_at.desc()))
    return [AlertOut.from_orm(a) for a in result.scalars().all()]


@router.get("/alerts/count")
async def alert_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.is_read == False))
    return {"unread": len(result.scalars().all())}


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404)
    a.is_read = True
    await db.commit()
    return {"ok": True}


@router.patch("/alerts/read-all")
async def mark_all_alerts_read(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.is_read == False))
    alerts = result.scalars().all()
    for a in alerts:
        a.is_read = True
    await db.commit()
    return {"marked": len(alerts)}
