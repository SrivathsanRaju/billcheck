"""Pincode zone validation — stub (provider-specific tables not available)."""
from typing import Optional


def validate_zone(origin: str, dest: str, provider: str = "") -> Optional[str]:
    """Returns None — requires provider-specific pincode→zone mapping tables."""
    return None


def derive_zone(origin: str, dest: str) -> Optional[str]:
    """Returns None — skipped to avoid false positives without real zone matrix."""
    return None
