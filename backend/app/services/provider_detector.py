def detect_provider(text: str) -> str:
    text_lower = text.lower()
    providers = {
        "BlueDart": ["bluedart", "blue dart"],
        "Delhivery": ["delhivery"],
        "DTDC": ["dtdc"],
        "FedEx": ["fedex", "fed ex"],
        "Ekart": ["ekart"],
        "Xpressbees": ["xpressbees", "xpress bees"],
        "Shadowfax": ["shadowfax"],
        "Ecom Express": ["ecom express", "ecom-express"],
    }
    for provider, keywords in providers.items():
        if any(kw in text_lower for kw in keywords):
            return provider
    return "Unknown"
