"""Cross-batch analytics."""
from typing import List, Any, Dict
from collections import defaultdict


def build_analytics(batches: List[Any], all_discrepancies: List[Any]) -> Dict:
    if not batches:
        return {
            "total_batches": 0,
            "total_invoices": 0,
            "total_overcharge": 0,
            "avg_overcharge_rate": 0,
            "monthly_trends": [],
            "provider_scorecards": [],
            "check_type_totals": [],
        }

    total_invoices = sum(b.total_invoices for b in batches)
    total_overcharge = sum(d.overcharge_amount for d in all_discrepancies)
    total_billed = sum(
        (b.summary or {}).get("total_billed", 0) for b in batches
    )
    avg_overcharge_rate = (total_overcharge / total_billed * 100) if total_billed > 0 else 0

    # Monthly trends
    monthly: Dict[str, Dict] = defaultdict(lambda: {"invoices": 0, "overcharge": 0, "discrepancies": 0})
    for b in batches:
        month = b.created_at.strftime("%Y-%m")
        monthly[month]["invoices"] += b.total_invoices
        summary = b.summary or {}
        monthly[month]["overcharge"] += summary.get("total_overcharge", 0)
    for d in all_discrepancies:
        # find batch month
        for b in batches:
            if b.id == d.batch_id:
                month = b.created_at.strftime("%Y-%m")
                monthly[month]["discrepancies"] += 1
                break

    monthly_trends = [
        {"month": k, **v} for k, v in sorted(monthly.items())
    ]

    # Provider scorecards
    by_provider: Dict[str, Dict] = defaultdict(lambda: {"batches": 0, "invoices": 0, "overcharge": 0, "discrepancies": 0})
    for b in batches:
        p = b.provider_name or "Unknown"
        by_provider[p]["batches"] += 1
        by_provider[p]["invoices"] += b.total_invoices
        by_provider[p]["overcharge"] += (b.summary or {}).get("total_overcharge", 0)
    for d in all_discrepancies:
        for b in batches:
            if b.id == d.batch_id:
                by_provider[b.provider_name or "Unknown"]["discrepancies"] += 1
                break

    provider_scorecards = [
        {"provider": k, **v} for k, v in by_provider.items()
    ]

    # Check type totals
    by_check: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "overcharge": 0})
    for d in all_discrepancies:
        by_check[d.check_type]["count"] += 1
        by_check[d.check_type]["overcharge"] += d.overcharge_amount
    check_type_totals = [
        {"check_type": k, **v} for k, v in sorted(by_check.items(), key=lambda x: -x[1]["overcharge"])
    ]

    return {
        "total_batches": len(batches),
        "total_invoices": total_invoices,
        "total_overcharge": round(total_overcharge, 2),
        "avg_overcharge_rate": round(avg_overcharge_rate, 2),
        "monthly_trends": monthly_trends,
        "provider_scorecards": provider_scorecards,
        "check_type_totals": check_type_totals,
    }
