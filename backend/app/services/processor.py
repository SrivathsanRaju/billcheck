"""Main batch processing orchestrator."""
import os
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db_models import ProcessingBatch, Invoice, Discrepancy, Alert
from app.models.schemas import InvoiceData, ContractData
from app.services.provider_detector import detect_provider
from app.core.config import settings


async def process_batch(batch_id: int, invoice_path: str, contract_path: str, db: AsyncSession):
    try:
        result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
        batch = result.scalar_one()
        batch.status = "processing"
        await db.commit()

        # Detect provider from file content
        try:
            with open(invoice_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read(2000)
            provider = detect_provider(raw_text)
        except Exception:
            provider = "Unknown"
        batch.provider_name = provider

        # --- Extract invoices ---
        invoices = await _extract_invoices(invoice_path)
        if not invoices:
            raise ValueError("No invoices could be parsed from the invoice file.")

        batch.total_invoices = len(invoices)
        await db.commit()

        # --- Extract contract ---
        contract = await _extract_contract(contract_path)

        # --- Save invoices to DB ---
        invoice_objs = []
        for inv in invoices:
            db_inv = Invoice(
                batch_id=batch_id,
                awb_number=inv.awb_number,
                shipment_date=inv.shipment_date or "",
                origin_pincode=inv.origin_pincode or "",
                destination_pincode=inv.destination_pincode or "",
                weight_billed=inv.weight_billed or 0,
                zone=inv.zone or "",
                base_freight=inv.base_freight or 0,
                cod_fee=inv.cod_fee or 0,
                rto_fee=inv.rto_fee or 0,
                fuel_surcharge=inv.fuel_surcharge or 0,
                other_surcharges=inv.other_surcharges or 0,
                gst_rate=inv.gst_rate or 18,
                total_billed=inv.total_billed or 0,
                raw_extracted=inv.model_dump(),
            )
            db.add(db_inv)
            invoice_objs.append((inv, db_inv))

        await db.flush()

        # --- Run rule engine checks ---
        all_discrepancies = _run_checks(invoices, contract)

        # Map awb -> db invoice id
        awb_to_id = {db_inv.awb_number: db_inv.id for _, db_inv in invoice_objs}

        for d in all_discrepancies:
            disc = Discrepancy(
                invoice_id=awb_to_id.get(d.awb_number, invoice_objs[0][1].id if invoice_objs else None),
                batch_id=batch_id,
                awb_number=d.awb_number or "",
                check_type=d.check_type,
                description=d.description,
                billed_value=d.billed_value,
                expected_value=d.expected_value,
                overcharge_amount=d.overcharge_amount,
                severity=d.severity,
                confidence_score=d.confidence_score,
                confidence_reason=d.confidence_reason,
            )
            db.add(disc)

        await db.flush()

        # --- Summary ---
        total_overcharge = sum(d.overcharge_amount for d in all_discrepancies)
        total_billed = sum(inv.total_billed or 0 for inv in invoices)
        overcharge_rate = (total_overcharge / total_billed * 100) if total_billed > 0 else 0

        severity_counts: dict = {}
        check_type_counts: dict = {}
        for d in all_discrepancies:
            severity_counts[d.severity] = severity_counts.get(d.severity, 0) + 1
            check_type_counts[d.check_type] = check_type_counts.get(d.check_type, 0) + 1

        batch.summary = {
            "total_invoices": len(invoices),
            "total_discrepancies": len(all_discrepancies),
            "total_overcharge": round(total_overcharge, 2),
            "total_billed": round(total_billed, 2),
            "overcharge_rate": round(overcharge_rate, 2),
            "severity_counts": severity_counts,
            "check_type_counts": check_type_counts,
        }
        batch.processed_invoices = len(invoices)
        batch.status = "completed"
        await db.commit()

        await _generate_alerts(batch, batch_id, all_discrepancies, overcharge_rate, total_overcharge, db)

    except Exception as e:
        traceback.print_exc()
        try:
            result = await db.execute(select(ProcessingBatch).where(ProcessingBatch.id == batch_id))
            batch = result.scalar_one_or_none()
            if batch:
                batch.status = "failed"
                batch.error_message = str(e)
                await db.commit()
        except Exception:
            pass


async def _extract_invoices(path: str):
    """Extract invoices — CSV fast path, PDF/image via Gemini if configured."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".csv":
            from app.services.invoice_extractor import extract_from_csv
            return await extract_from_csv(path)
        elif ext == ".pdf":
            from app.services.invoice_extractor import extract_from_pdf
            return await extract_from_pdf(path)
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            from app.services.invoice_extractor import extract_from_image
            return await extract_from_image(path)
        else:
            from app.services.invoice_extractor import extract_from_csv
            return await extract_from_csv(path)
    except Exception as e:
        # Final fallback to basic CSV parser
        from app.services.csv_fast_extractor import parse_invoice_csv
        from app.models.schemas import InvoiceData
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            rows = parse_invoice_csv(f.read())
        return [InvoiceData(**r) for r in rows if r.get("awb_number")]


async def _extract_contract(path: str) -> ContractData:
    """Extract contract — CSV direct parse, PDF/image via Gemini if configured."""
    ext = os.path.splitext(path)[1].lower()
    try:
        from app.services.contract_extractor import extract_contract
        return await extract_contract(path)
    except Exception:
        # Fallback to basic parser
        from app.services.csv_fast_extractor import parse_contract_csv
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = parse_contract_csv(f.read())
        return ContractData(
            cod_rate=data.get("cod_percentage", 1.5),
            rto_rate=data.get("rto_percentage", 50.0),
            fuel_surcharge_pct=data.get("fuel_surcharge_percentage", 12.0),
            gst_pct=data.get("gst_percentage", 18.0),
        )


def _run_checks(invoices, contract: ContractData):
    """Run all rule engine checks, handle duplicate AWB across invoices."""
    from app.services.rule_engine import ALL_CHECKS
    from app.models.schemas import DiscrepancyResult

    results = []
    awb_seen = {}

    for inv in invoices:
        awb = inv.awb_number

        # Duplicate AWB check
        if awb in awb_seen:
            results.append(DiscrepancyResult(
                check_type="duplicate_awb",
                severity="critical",
                description=f"AWB {awb} billed more than once",
                billed_value=inv.total_billed,
                expected_value=0,
                overcharge_amount=inv.total_billed or 0,
                confidence_score=1.0,
                confidence_reason="Exact AWB match — definitive duplicate.",
                awb_number=awb,
            ))
        awb_seen[awb] = True

        # Run all rule engine checks
        for check_fn in ALL_CHECKS:
            try:
                result = check_fn(inv, contract)
                if result:
                    result.awb_number = awb
                    results.append(result)
            except Exception:
                pass

    return results


async def _generate_alerts(batch, batch_id, discrepancies, overcharge_rate, total_overcharge, db: AsyncSession):
    alerts = []

    if overcharge_rate > 10:
        alerts.append(Alert(
            batch_id=batch_id, provider_name=batch.provider_name,
            alert_type="high_overcharge_rate", title="High Overcharge Rate Detected",
            message=f"Overcharge rate of {overcharge_rate:.1f}% exceeds 10% threshold in batch #{batch_id}.",
            severity="critical", value=overcharge_rate, threshold=10.0,
        ))
    elif overcharge_rate > 5:
        alerts.append(Alert(
            batch_id=batch_id, provider_name=batch.provider_name,
            alert_type="moderate_overcharge_rate", title="Moderate Overcharge Rate",
            message=f"Overcharge rate of {overcharge_rate:.1f}% exceeds 5% threshold in batch #{batch_id}.",
            severity="high", value=overcharge_rate, threshold=5.0,
        ))

    if total_overcharge > 5000:
        alerts.append(Alert(
            batch_id=batch_id, provider_name=batch.provider_name,
            alert_type="large_absolute_overcharge", title="Large Overcharge Amount",
            message=f"Total overcharge of ₹{total_overcharge:,.2f} exceeds ₹5,000 in batch #{batch_id}.",
            severity="critical", value=total_overcharge, threshold=5000.0,
        ))

    criticals = [d for d in discrepancies if d.severity == "critical"]
    if len(criticals) >= 3:
        alerts.append(Alert(
            batch_id=batch_id, provider_name=batch.provider_name,
            alert_type="multiple_critical", title="Multiple Critical Discrepancies",
            message=f"{len(criticals)} critical discrepancies in batch #{batch_id}.",
            severity="critical", value=len(criticals), threshold=3.0,
        ))

    duplicates = [d for d in discrepancies if d.check_type == "duplicate_awb"]
    if duplicates:
        alerts.append(Alert(
            batch_id=batch_id, provider_name=batch.provider_name,
            alert_type="duplicate_awbs", title="Duplicate AWBs Detected",
            message=f"{len(duplicates)} duplicate AWB(s) in batch #{batch_id}.",
            severity="high", value=len(duplicates), threshold=1.0,
        ))

    for a in alerts:
        db.add(a)
    await db.commit()
