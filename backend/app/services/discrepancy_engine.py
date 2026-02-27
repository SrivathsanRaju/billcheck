"""All 10 billing checks."""
from typing import List, Dict, Any


def _severity(overcharge: float) -> str:
    if overcharge >= 500:
        return "critical"
    elif overcharge >= 200:
        return "high"
    elif overcharge >= 50:
        return "medium"
    return "low"


def run_all_checks(invoices: List[Dict], contract: Dict) -> List[Dict]:
    """Run all 10 checks. Returns list of discrepancy dicts."""
    discrepancies = []
    awb_seen: Dict[str, int] = {}

    for inv in invoices:
        awb = inv["awb_number"]
        results = []

        # 1. Duplicate AWB
        if awb in awb_seen:
            results.append({
                "check_type": "duplicate_awb",
                "description": f"AWB {awb} billed more than once (first seen at row {awb_seen[awb]})",
                "billed_value": inv["total_billed"],
                "expected_value": 0,
                "overcharge_amount": inv["total_billed"],
                "severity": "critical",
                "confidence_score": 1.0,
                "confidence_reason": "Exact AWB match — definitive duplicate.",
            })
        awb_seen[awb] = inv.get("_row", 0)

        # 2. Weight overcharge (if zone rates available)
        zone = (inv.get("zone") or "").upper()
        zone_rate = contract.get("zones", {}).get(zone, 0)
        if zone_rate > 0 and inv["weight_billed"] > 0:
            expected_freight = zone_rate * inv["weight_billed"]
            if inv["base_freight"] > expected_freight * 1.01:
                diff = inv["base_freight"] - expected_freight
                results.append({
                    "check_type": "weight_overcharge",
                    "description": f"Base freight ₹{inv['base_freight']:.2f} exceeds expected ₹{expected_freight:.2f} for {inv['weight_billed']}kg in zone {zone}",
                    "billed_value": inv["base_freight"],
                    "expected_value": expected_freight,
                    "overcharge_amount": diff,
                    "severity": _severity(diff),
                    "confidence_score": 0.9,
                    "confidence_reason": "Computed from contracted zone rate × billed weight.",
                })

        # 3. Zone mismatch
        origin = inv.get("origin_pincode", "")
        dest = inv.get("destination_pincode", "")
        if origin and dest and zone:
            derived_zone = _derive_zone(origin, dest)
            if derived_zone and derived_zone != zone:
                results.append({
                    "check_type": "zone_mismatch",
                    "description": f"Billed zone {zone} but origin→destination pincodes suggest zone {derived_zone}",
                    "billed_value": None,
                    "expected_value": None,
                    "overcharge_amount": _zone_overcharge(zone, derived_zone, inv["base_freight"]),
                    "severity": "high",
                    "confidence_score": 0.75,
                    "confidence_reason": "Zone derived from pincode ranges; may differ by courier service.",
                })

        # 4. Rate deviation
        if zone_rate > 0 and inv["weight_billed"] > 0:
            expected_freight = zone_rate * inv["weight_billed"]
            deviation_pct = abs(inv["base_freight"] - expected_freight) / max(expected_freight, 1) * 100
            if deviation_pct > 5 and inv["base_freight"] > expected_freight:
                diff = inv["base_freight"] - expected_freight
                results.append({
                    "check_type": "rate_deviation",
                    "description": f"Base freight deviates {deviation_pct:.1f}% from contract rate",
                    "billed_value": inv["base_freight"],
                    "expected_value": expected_freight,
                    "overcharge_amount": diff,
                    "severity": "high" if deviation_pct > 15 else "medium",
                    "confidence_score": 0.85,
                    "confidence_reason": f"{deviation_pct:.1f}% deviation from contracted zone rate.",
                })

        # 5. COD fee mismatch
        if inv["cod_fee"] > 0:
            cod_pct = contract.get("cod_percentage", 1.5)
            expected_cod = inv["total_billed"] * cod_pct / 100
            if inv["cod_fee"] > expected_cod * 1.05:
                diff = inv["cod_fee"] - expected_cod
                results.append({
                    "check_type": "cod_fee_mismatch",
                    "description": f"COD fee ₹{inv['cod_fee']:.2f} exceeds contracted {cod_pct}% = ₹{expected_cod:.2f}",
                    "billed_value": inv["cod_fee"],
                    "expected_value": expected_cod,
                    "overcharge_amount": diff,
                    "severity": _severity(diff),
                    "confidence_score": 0.88,
                    "confidence_reason": f"Contract COD = {cod_pct}% of invoice value.",
                })

        # 6. RTO overcharge
        if inv["rto_fee"] > 0:
            rto_pct = contract.get("rto_percentage", 50.0)
            expected_rto = inv["base_freight"] * rto_pct / 100
            if inv["rto_fee"] > expected_rto * 1.05:
                diff = inv["rto_fee"] - expected_rto
                results.append({
                    "check_type": "rto_overcharge",
                    "description": f"RTO fee ₹{inv['rto_fee']:.2f} exceeds contracted {rto_pct}% of base freight = ₹{expected_rto:.2f}",
                    "billed_value": inv["rto_fee"],
                    "expected_value": expected_rto,
                    "overcharge_amount": diff,
                    "severity": _severity(diff),
                    "confidence_score": 0.87,
                    "confidence_reason": f"Contract RTO = {rto_pct}% of base freight.",
                })

        # 7. Fuel surcharge mismatch
        fuel_pct = contract.get("fuel_surcharge_percentage", 12.0)
        expected_fuel = inv["base_freight"] * fuel_pct / 100
        if inv["fuel_surcharge"] > expected_fuel * 1.05 and inv["base_freight"] > 0:
            diff = inv["fuel_surcharge"] - expected_fuel
            results.append({
                "check_type": "fuel_surcharge_mismatch",
                "description": f"Fuel surcharge ₹{inv['fuel_surcharge']:.2f} exceeds contracted {fuel_pct}% = ₹{expected_fuel:.2f}",
                "billed_value": inv["fuel_surcharge"],
                "expected_value": expected_fuel,
                "overcharge_amount": diff,
                "severity": _severity(diff),
                "confidence_score": 0.9,
                "confidence_reason": f"Contract fuel surcharge = {fuel_pct}% of base freight.",
            })

        # 8. Non-contracted surcharge
        if inv["other_surcharges"] > 0:
            contracted_surcharges = contract.get("contracted_surcharges", [])
            if not contracted_surcharges:
                results.append({
                    "check_type": "non_contracted_surcharge",
                    "description": f"Other surcharges ₹{inv['other_surcharges']:.2f} billed but not in contract",
                    "billed_value": inv["other_surcharges"],
                    "expected_value": 0,
                    "overcharge_amount": inv["other_surcharges"],
                    "severity": "medium",
                    "confidence_score": 0.7,
                    "confidence_reason": "No contracted surcharges found; may be legitimate if contract omits them.",
                })

        # 9. GST miscalculation
        gst_pct = contract.get("gst_percentage", 18.0)
        subtotal = inv["base_freight"] + inv["cod_fee"] + inv["rto_fee"] + inv["fuel_surcharge"] + inv["other_surcharges"]
        if subtotal > 0:
            expected_gst = subtotal * gst_pct / 100
            billed_gst = inv["total_billed"] - subtotal
            if billed_gst > 0 and abs(billed_gst - expected_gst) > expected_gst * 0.03:
                if billed_gst > expected_gst:
                    diff = billed_gst - expected_gst
                    results.append({
                        "check_type": "gst_miscalculation",
                        "description": f"GST billed ₹{billed_gst:.2f} vs expected ₹{expected_gst:.2f} at {gst_pct}%",
                        "billed_value": billed_gst,
                        "expected_value": expected_gst,
                        "overcharge_amount": diff,
                        "severity": _severity(diff),
                        "confidence_score": 0.93,
                        "confidence_reason": f"GST = {gst_pct}% of pre-tax subtotal; arithmetic check.",
                    })

        # 10. Arithmetic total mismatch
        computed_total = subtotal * (1 + gst_pct / 100)
        if inv["total_billed"] > 0 and abs(inv["total_billed"] - computed_total) > 1.0 and inv["total_billed"] > computed_total:
            diff = inv["total_billed"] - computed_total
            results.append({
                "check_type": "arithmetic_total_mismatch",
                "description": f"Row total ₹{inv['total_billed']:.2f} ≠ computed ₹{computed_total:.2f}",
                "billed_value": inv["total_billed"],
                "expected_value": computed_total,
                "overcharge_amount": diff,
                "severity": _severity(diff),
                "confidence_score": 0.95,
                "confidence_reason": "Pure arithmetic check of line items vs total.",
            })

        for r in results:
            r["awb_number"] = awb

        discrepancies.extend(results)

    return discrepancies


def _derive_zone(origin: str, dest: str) -> str:
    """Simple zone derivation from first 3 digits of pincode."""
    try:
        o = int(origin[:3])
        d = int(dest[:3])
        diff = abs(o - d)
        if diff == 0:
            return "LOCAL"
        elif diff <= 30:
            return "ZONE_A"
        elif diff <= 100:
            return "ZONE_B"
        elif diff <= 300:
            return "ZONE_C"
        else:
            return "ZONE_D"
    except Exception:
        return ""


def _zone_overcharge(billed_zone: str, expected_zone: str, base_freight: float) -> float:
    zone_order = ["LOCAL", "ZONE_A", "ZONE_B", "ZONE_C", "ZONE_D"]
    try:
        bi = zone_order.index(billed_zone)
        ei = zone_order.index(expected_zone)
        if bi > ei:
            return base_freight * 0.15 * (bi - ei)
    except Exception:
        pass
    return 0.0
