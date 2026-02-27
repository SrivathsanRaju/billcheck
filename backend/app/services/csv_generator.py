"""Export CSVs from batch data."""
import csv
import io
from typing import List, Any


def generate_discrepancy_csv(discrepancies: List[Any]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ID", "AWB Number", "Check Type", "Description", "Billed Value",
        "Expected Value", "Overcharge Amount (INR)", "Severity",
        "Confidence Score", "Dispute Status"
    ])
    for d in discrepancies:
        writer.writerow([
            d.id, d.awb_number, d.check_type, d.description,
            d.billed_value or "", d.expected_value or "",
            f"{d.overcharge_amount:.2f}", d.severity,
            f"{d.confidence_score:.2f}", d.dispute_status
        ])
    return out.getvalue()


def generate_summary_csv(batch: Any, discrepancies: List[Any]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    summary = batch.summary or {}
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Batch ID", batch.id])
    writer.writerow(["Provider", batch.provider_name])
    writer.writerow(["Status", batch.status])
    writer.writerow(["Total Invoices", batch.total_invoices])
    writer.writerow(["Total Discrepancies", len(discrepancies)])
    writer.writerow(["Total Overcharge (INR)", summary.get("total_overcharge", 0)])
    writer.writerow(["Overcharge Rate (%)", summary.get("overcharge_rate", 0)])
    return out.getvalue()


def generate_payout_csv(invoices: List[Any], discrepancies: List[Any]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["AWB Number", "Total Billed (INR)", "Total Overcharge (INR)", "Payable Amount (INR)"])
    disc_by_awb: dict = {}
    for d in discrepancies:
        disc_by_awb[d.awb_number] = disc_by_awb.get(d.awb_number, 0) + d.overcharge_amount
    for inv in invoices:
        overcharge = disc_by_awb.get(inv.awb_number, 0)
        payable = inv.total_billed - overcharge
        writer.writerow([inv.awb_number, f"{inv.total_billed:.2f}", f"{overcharge:.2f}", f"{payable:.2f}"])
    return out.getvalue()
