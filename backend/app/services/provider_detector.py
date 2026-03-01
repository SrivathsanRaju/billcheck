"""
Universal provider detector — scans full file content for provider name.
Covers all major Indian logistics providers.
"""

PROVIDER_KEYWORDS = {
    "BlueDart":     ["bluedart", "blue dart", "blue-dart"],
    "Delhivery":    ["delhivery"],
    "DTDC":         ["dtdc"],
    "Ekart":        ["ekart", "e-kart"],
    "XpressBees":   ["xpressbees", "xpress bees", "xpress-bees"],
    "Shadowfax":    ["shadowfax", "shadow fax"],
    "Ecom Express": ["ecom express", "ecom-express", "ecomexpress"],
    "FedEx":        ["fedex", "fed ex", "fed-ex"],
    "DHL":          ["dhl express", " dhl "],
    "Smartr":       ["smartr logistics", "smartr"],
    "Borzo":        ["borzo"],
    "Dunzo":        ["dunzo"],
    "Flipkart":     ["flipkart logistics", "fkl"],
    "Amazon":       ["amazon logistics", "amazon transportation"],
    "Meesho":       ["meesho"],
}

def detect_provider(text: str) -> str:
    """
    Detect provider from invoice/contract text.
    Scans full text (not just first N chars).
    Returns provider name or 'Unknown'.
    """
    text_lower = text.lower()
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return provider
    return "Unknown"
