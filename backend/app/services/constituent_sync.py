"""
Constituent Synchronization & Surveillance Filter Service.
Maintains official index constituents for Nifty Midcap 150/100 and Nifty Smallcap 250/100,
validates series ('EQ' only), and excludes stocks under ASM/GSM Stage 2+ surveillance.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class ConstituentMetadata:
    symbol: str
    company_name: str
    market_cap_tier: str  # MIDCAP | SMALLCAP
    index_name: str       # NIFTYMIDCAP150 | NIFTYSMALLCAP250
    sector: str
    series: str = "EQ"
    asm_stage: int = 0    # 0 = none, 1 = stage 1, 2+ = stage 2+ (excluded)
    gsm_stage: int = 0    # 0 = none, 1 = stage 1, 2+ = stage 2+ (excluded)
    is_active: bool = True


# ─── Official Nifty Midcap 150 & Smallcap 250 Curated Constituents ─────────────

NIFTY_MIDCAP_150_CONSTITUENTS: Dict[str, Dict] = {
    "POLYCAB":    {"name": "Polycab India Ltd.", "sector": "Electricals", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "TRENT":      {"name": "Trent Ltd.", "sector": "Retail", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "CUMMINSIND": {"name": "Cummins India Ltd.", "sector": "Engineering", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "DIXON":      {"name": "Dixon Technologies Ltd.", "sector": "Electronics & EMS", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "PERSISTENT": {"name": "Persistent Systems Ltd.", "sector": "IT", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "COFORGE":    {"name": "Coforge Ltd.", "sector": "IT", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "KAYNES":     {"name": "Kaynes Technology India Ltd.", "sector": "Defense & EMS", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "SUZLON":     {"name": "Suzlon Energy Ltd.", "sector": "Renewable Energy", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "KPITTECH":   {"name": "KPIT Technologies Ltd.", "sector": "Auto Tech", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "FEDERALBNK": {"name": "The Federal Bank Ltd.", "sector": "Banking", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "PRESTIGE":   {"name": "Prestige Estates Projects Ltd.", "sector": "Real Estate", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "HAL":        {"name": "Hindustan Aeronautics Ltd.", "sector": "Defense & Aerospace", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "BEL":        {"name": "Bharat Electronics Ltd.", "sector": "Defense Electronics", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "BHEL":       {"name": "Bharat Heavy Electricals Ltd.", "sector": "Capital Goods", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "ZOMATO":     {"name": "Zomato Ltd.", "sector": "Tech", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "PAYTM":      {"name": "One97 Communications Ltd.", "sector": "Tech", "tier": "MIDCAP", "asm": 1, "gsm": 0},
    "APOLLOTYRE": {"name": "Apollo Tyres Ltd.", "sector": "Auto Ancillary", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "MAXHEALTH":  {"name": "Max Healthcare Institute Ltd.", "sector": "Healthcare", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "ASTRAL":     {"name": "Astral Ltd.", "sector": "Building Materials", "tier": "MIDCAP", "asm": 0, "gsm": 0},
    "VOLTAS":     {"name": "Voltas Ltd.", "sector": "Consumer Durables", "tier": "MIDCAP", "asm": 0, "gsm": 0},
}

NIFTY_SMALLCAP_250_CONSTITUENTS: Dict[str, Dict] = {
    "DATAPATTNS": {"name": "Data Patterns (India) Ltd.", "sector": "Defense Electronics", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "MAPMYINDIA": {"name": "C.E. Info Systems Ltd.", "sector": "Tech & SaaS", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "CENTURYPLY": {"name": "Century Plyboards Ltd.", "sector": "Building Materials", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "TEJASNET":   {"name": "Tejas Networks Ltd.", "sector": "Telecom Equipment", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "GRAVITA":    {"name": "Gravita India Ltd.", "sector": "Recycling & Metals", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "ELECON":     {"name": "Elecon Engineering Co. Ltd.", "sector": "Industrial Machinery", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "NEWGEN":     {"name": "Newgen Software Technologies", "sector": "Enterprise Software", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "ANANDRATHI": {"name": "Anand Rathi Wealth Ltd.", "sector": "Wealth Management", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "NEULANDLAB": {"name": "Neuland Laboratories Ltd.", "sector": "Pharma & API", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "TITAGARH":   {"name": "Titagarh Rail Systems Ltd.", "sector": "Railways & Defense", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "JWL":        {"name": "Jupiter Wagons Ltd.", "sector": "Railways & Logistics", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "MARKSANS":   {"name": "Marksans Pharma Ltd.", "sector": "Pharma", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "KIMS":       {"name": "Krishna Institute of Medical Sciences", "sector": "Healthcare", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "BLS":        {"name": "BLS International Services Ltd.", "sector": "Tech Services", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "IONEXCHANG": {"name": "ION Exchange (India) Ltd.", "sector": "Water & Engineering", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
    "KEC":        {"name": "KEC International Ltd.", "sector": "Power Infrastructure", "tier": "SMALLCAP", "asm": 0, "gsm": 0},
}


class ConstituentRegistry:
    """Registry maintaining active constituent definitions, series verification, and surveillance status."""

    def __init__(self):
        self._midcap_symbols: Set[str] = set(NIFTY_MIDCAP_150_CONSTITUENTS.keys())
        self._smallcap_symbols: Set[str] = set(NIFTY_SMALLCAP_250_CONSTITUENTS.keys())

    def is_eligible_series(self, series: str) -> bool:
        """Series must strictly be EQ. Exclude BE (trade to trade), SM (SME), ST."""
        return series.strip().upper() == "EQ"

    def passes_surveillance(self, symbol: str) -> bool:
        """
        Check if stock passes SEBI/NSE surveillance filters.
        Excludes stocks in ASM Stage 2+ or GSM Stage 2+.
        """
        meta = self.get_metadata(symbol)
        if not meta:
            return True
        # Exclude ASM Stage 2+ or GSM Stage 2+
        if meta.asm_stage >= 2 or meta.gsm_stage >= 2:
            return False
        return True

    def get_tier(self, symbol: str) -> Optional[str]:
        """Return MIDCAP, SMALLCAP, or None if outside universe."""
        sym = symbol.strip().upper()
        if sym in self._midcap_symbols:
            return "MIDCAP"
        if sym in self._smallcap_symbols:
            return "SMALLCAP"
        return None

    def get_benchmark_index(self, symbol: str) -> str:
        """Return the appropriate benchmark index for Mansfield Relative Strength."""
        tier = self.get_tier(symbol)
        if tier == "SMALLCAP":
            return "NIFTYSMALLCAP250"
        return "NIFTYMIDCAP150"

    def get_metadata(self, symbol: str) -> Optional[ConstituentMetadata]:
        """Retrieve full constituent metadata."""
        sym = symbol.strip().upper()
        if sym in NIFTY_MIDCAP_150_CONSTITUENTS:
            c = NIFTY_MIDCAP_150_CONSTITUENTS[sym]
            return ConstituentMetadata(
                symbol=sym,
                company_name=c["name"],
                market_cap_tier=c["tier"],
                index_name="NIFTYMIDCAP150",
                sector=c["sector"],
                asm_stage=c.get("asm", 0),
                gsm_stage=c.get("gsm", 0),
            )
        elif sym in NIFTY_SMALLCAP_250_CONSTITUENTS:
            c = NIFTY_SMALLCAP_250_CONSTITUENTS[sym]
            return ConstituentMetadata(
                symbol=sym,
                company_name=c["name"],
                market_cap_tier=c["tier"],
                index_name="NIFTYSMALLCAP250",
                sector=c["sector"],
                asm_stage=c.get("asm", 0),
                gsm_stage=c.get("gsm", 0),
            )
        return None

    def get_all_symbols(self, tier: str = "ALL") -> List[str]:
        """Get list of symbols matching the requested tier."""
        tier_clean = tier.strip().upper()
        if tier_clean == "MIDCAP":
            return sorted(list(self._midcap_symbols))
        elif tier_clean == "SMALLCAP":
            return sorted(list(self._smallcap_symbols))
        return sorted(list(self._midcap_symbols | self._smallcap_symbols))


constituent_registry = ConstituentRegistry()
