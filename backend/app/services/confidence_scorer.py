"""Confidence scoring for each check type."""
from typing import Tuple


def score_weight_check(billed: float, expected: float) -> Tuple[float, str]:
    pct = abs(billed - expected) / max(expected, 0.01)
    if pct > 0.20:
        return 0.95, f"Large deviation of {pct:.1%} from contracted rate."
    return 0.85, f"Deviation of {pct:.1%} from contracted rate."


def score_rate_check(billed: float, expected: float) -> Tuple[float, str]:
    pct = abs(billed - expected) / max(expected, 0.01)
    if pct > 0.15:
        return 0.92, f"Rate deviation of {pct:.1%} exceeds tolerance."
    return 0.80, f"Rate deviation of {pct:.1%}."


def score_zone_check(billed_zone: str, expected_zone: str) -> Tuple[float, str]:
    return 0.70, f"Zone {billed_zone} billed but {expected_zone} derived from pincodes."


def score_gst_check(billed_gst: float, expected_gst: float) -> Tuple[float, str]:
    return 0.93, f"GST billed ₹{billed_gst:.2f} vs expected ₹{expected_gst:.2f}."


def score_duplicate_check() -> Tuple[float, str]:
    return 1.0, "Exact AWB match — definitive duplicate."


def score_arithmetic_check(billed: float, calculated: float) -> Tuple[float, str]:
    return 0.95, f"Arithmetic check: billed ₹{billed:.2f} vs calculated ₹{calculated:.2f}."
