"""
Penny Stock Surveillance & Market Universe Filter Module.
Specialized for Indian Equities (NSE / BSE).

Enforces mandatory regulatory & survival pre-filters:
1. Universe: Price ₹5.00 - ₹50.00, Market Cap < ₹500 Cr, Series 'EQ' (NSE) or 'A'/'B' (BSE).
2. Surveillance Exclusions: Immediate exclusion of scrips in GSM Stage 1-4, ESM Stage 1-2, or Long-Term/Short-Term ASM.
3. Circuit Limit Filter: Requires minimum daily price band of 10% or 20%. Discards 2% or 5% clamped scrips.
4. No Frozen Circuit Closes: Close must NOT equal Upper Circuit Limit with zero ask volume; requires two-way traded liquidity.
5. Liquidity & Spread Check: Turnover >= ₹2.5 Cr, Unique Trades/day >= 2,500, Bid-Ask spread <= 0.8% of share price.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import date


@dataclass
class PennyStockMetadata:
    symbol: str
    company_name: str
    exchange: str               # NSE | BSE
    series: str                 # EQ, A, B
    market_cap_cr: float        # Under ₹500 Cr
    sector: str
    price_band_pct: float       # 10.0 or 20.0 (discard 2.0 or 5.0)
    gsm_stage: int = 0          # 0 = clean, 1-4 = excluded
    esm_stage: int = 0          # 0 = clean, 1-2 = excluded
    asm_stage: int = 0          # 0 = clean, 1+ = excluded (Long-term / Short-term ASM)
    is_circuit_locked: bool = False
    daily_trades_avg: int = 3500
    bid_ask_spread_pct: float = 0.45


# ─── Curated Penny Stock Master with Exchange Surveillance Metadata ──────────
# Strictly contains scrips with Market Cap < ₹500 Cr and Prices within ₹5 - ₹50.
# Includes clean candidates, as well as tracked scrips with surveillance tags for filter testing.

PENNY_STOCK_MASTER: Dict[str, Dict] = {
    # Clean Candidates (Pass survival filters: Price ₹5-₹50, MCap < ₹500Cr, 10% or 20% bands, 0 ASM/GSM/ESM)
    "URJA": {
        "name": "Urja Global Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 320.0,
        "sector": "Renewable Energy & Solar",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 6200,
        "bid_ask_spread_pct": 0.42,
    },
    "FCSSOFT": {
        "name": "FCS Software Solutions Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 280.0,
        "sector": "IT & Software Services",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 5400,
        "bid_ask_spread_pct": 0.38,
    },
    "ORIENTALTL": {
        "name": "Oriental Trimex Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 145.0,
        "sector": "Building Products & Marble",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 4100,
        "bid_ask_spread_pct": 0.55,
    },
    "SEPOWER": {
        "name": "S.E. Power Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 195.0,
        "sector": "Non-Conventional Energy",
        "price_band_pct": 10.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 3800,
        "bid_ask_spread_pct": 0.62,
    },
    "SHRENIK": {
        "name": "Shrenik Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 115.0,
        "sector": "Paper & Forest Products",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 4900,
        "bid_ask_spread_pct": 0.48,
    },
    "VARDHMAN": {
        "name": "Vardhman Polytex Ltd.",
        "exchange": "BSE",
        "series": "B",
        "market_cap_cr": 210.0,
        "sector": "Textiles & Apparel",
        "price_band_pct": 10.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 3200,
        "bid_ask_spread_pct": 0.58,
    },
    "SALONA": {
        "name": "Salona Cotspin Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 165.0,
        "sector": "Textiles & Yarns",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 3600,
        "bid_ask_spread_pct": 0.52,
    },
    "MITTAL": {
        "name": "Mittal Life Style Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 135.0,
        "sector": "Textile Trading",
        "price_band_pct": 10.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 3100,
        "bid_ask_spread_pct": 0.65,
    },
    "VIKASPROP": {
        "name": "Vikas Proppant & Granite",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 185.0,
        "sector": "Mining & Minerals",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 5100,
        "bid_ask_spread_pct": 0.44,
    },
    "CREATIVE": {
        "name": "Creative Castings Ltd.",
        "exchange": "BSE",
        "series": "B",
        "market_cap_cr": 190.0,
        "sector": "Industrial Castings",
        "price_band_pct": 20.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 2900,
        "bid_ask_spread_pct": 0.60,
    },

    # Disqualified Scrips for Verification (ASM / GSM / ESM / 2%-5% Circuit limits)
    "TRAP_GSM": {
        "name": "Operator Trap GSM Ltd.",
        "exchange": "NSE",
        "series": "EQ",
        "market_cap_cr": 85.0,
        "sector": "Shell / Speculative",
        "price_band_pct": 5.0,  # Clamped at 5%
        "gsm_stage": 2,         # Disqualified: GSM Stage 2
        "esm_stage": 0,
        "asm_stage": 0,
        "daily_trades_avg": 800,
        "bid_ask_spread_pct": 2.4,
    },
    "TRAP_ESM": {
        "name": "Illiquid ESM Micro Ltd.",
        "exchange": "BSE",
        "series": "T",
        "market_cap_cr": 45.0,
        "sector": "Trading",
        "price_band_pct": 2.0,  # Clamped at 2%
        "gsm_stage": 0,
        "esm_stage": 1,         # Disqualified: ESM Stage 1
        "asm_stage": 0,
        "daily_trades_avg": 300,
        "bid_ask_spread_pct": 3.8,
    },
    "TRAP_ASM": {
        "name": "High Volatility Spec Ltd.",
        "exchange": "NSE",
        "series": "BE",        # Trade-to-trade series
        "market_cap_cr": 220.0,
        "sector": "Finance",
        "price_band_pct": 5.0,
        "gsm_stage": 0,
        "esm_stage": 0,
        "asm_stage": 1,         # Disqualified: ASM Short-term
        "daily_trades_avg": 1200,
        "bid_ask_spread_pct": 1.5,
    },
}


class PennySurveillanceFilter:
    """
    Evaluates penny stocks against all SEBI/NSE/BSE regulatory, circuit band,
    and liquidity pre-filters before allowing pattern screening.
    """

    def __init__(self, master: Optional[Dict[str, Dict]] = None):
        self.master = master or PENNY_STOCK_MASTER

    def get_metadata(self, symbol: str) -> Optional[PennyStockMetadata]:
        sym = symbol.strip().upper()
        if sym in self.master:
            data = self.master[sym]
            return PennyStockMetadata(
                symbol=sym,
                company_name=data["name"],
                exchange=data.get("exchange", "NSE"),
                series=data.get("series", "EQ"),
                market_cap_cr=data.get("market_cap_cr", 200.0),
                sector=data.get("sector", "Diversified"),
                price_band_pct=data.get("price_band_pct", 20.0),
                gsm_stage=data.get("gsm_stage", 0),
                esm_stage=data.get("esm_stage", 0),
                asm_stage=data.get("asm_stage", 0),
                daily_trades_avg=data.get("daily_trades_avg", 3500),
                bid_ask_spread_pct=data.get("bid_ask_spread_pct", 0.45),
            )
        return None

    def evaluate_survival_gates(
        self,
        symbol: str,
        close_price: float,
        turnover_cr: float,
        daily_trades: int,
        high_price: float,
        low_price: float,
        prev_close: float,
    ) -> Tuple[bool, List[str], Dict[str, any]]:
        """
        Runs all survival gates. Returns: (passes_all, rejection_reasons, diagnostic_info)
        """
        rejections: List[str] = []
        meta = self.get_metadata(symbol)

        # 1. Price Boundary Check (₹5.00 - ₹50.00)
        if close_price < 5.00:
            rejections.append(f"Price ₹{close_price:.2f} < ₹5.00 minimum boundary (sub-₹1/micro illiquid risk)")
        elif close_price > 50.00:
            rejections.append(f"Price ₹{close_price:.2f} > ₹50.00 (exceeds penny stock definition)")

        if not meta:
            # If not in master, apply default checks
            if turnover_cr < 2.5:
                rejections.append(f"Turnover ₹{turnover_cr:.2f}Cr < ₹2.5Cr liquidity gate")
            return len(rejections) == 0, rejections, {"price_band_pct": 20.0, "safe": len(rejections) == 0}

        # 2. Market Capitalization Check (< ₹500 Cr)
        if meta.market_cap_cr >= 500.0:
            rejections.append(f"Market cap ₹{meta.market_cap_cr:.1f}Cr >= ₹500Cr limit")

        # 3. Exchange Segment / Series Check
        if meta.exchange == "NSE" and meta.series != "EQ":
            rejections.append(f"NSE series '{meta.series}' rejected (strictly 'EQ' required, no BE/SM/ST)")
        elif meta.exchange == "BSE" and meta.series not in ["A", "B"]:
            rejections.append(f"BSE series '{meta.series}' rejected (strictly 'A' or 'B' required, no T/Z)")

        # 4. Exchange Surveillance Disqualifications (GSM 1-4, ESM 1-2, ASM)
        if meta.gsm_stage > 0:
            rejections.append(f"Discarded: Active GSM (Graded Surveillance Measure) Stage {meta.gsm_stage}")
        if meta.esm_stage > 0:
            rejections.append(f"Discarded: Active ESM (Enhanced Surveillance Measure) Stage {meta.esm_stage}")
        if meta.asm_stage > 0:
            rejections.append(f"Discarded: Active ASM (Additional Surveillance Measure) Stage {meta.asm_stage}")

        # 5. Circuit Limit Filter (Must be 10% or 20%, discard 2% and 5%)
        if meta.price_band_pct not in [10.0, 20.0]:
            rejections.append(f"Discarded: Circuit price band clamped at {meta.price_band_pct}% (lower-circuit trap risk)")

        # 6. Frozen Circuit Closes (Close == Upper Circuit Limit with zero two-way liquidity)
        if prev_close > 0 and meta.price_band_pct in [10.0, 20.0]:
            upper_limit = round(prev_close * (1.0 + meta.price_band_pct / 100.0), 2)
            # Circuit lock occurs if close == high == upper_limit and close == low
            if close_price >= upper_limit and abs(high_price - low_price) < 0.02:
                rejections.append("Discarded: Frozen Upper Circuit lock with zero two-way liquidity")

        # 7. Liquidity & Spread Criteria
        if turnover_cr < 2.5:
            rejections.append(f"Daily Turnover ₹{turnover_cr:.2f}Cr < ₹2.5Cr survival threshold")

        trades_count = max(daily_trades, meta.daily_trades_avg)
        if trades_count < 2500:
            rejections.append(f"Trade count {trades_count} < 2,500 unique trades/day minimum")

        if meta.bid_ask_spread_pct > 0.8:
            rejections.append(f"Bid-Ask spread {meta.bid_ask_spread_pct:.2f}% > 0.8% threshold")

        passes = len(rejections) == 0
        diagnostics = {
            "symbol": symbol,
            "company_name": meta.company_name,
            "exchange": meta.exchange,
            "series": meta.series,
            "market_cap_cr": meta.market_cap_cr,
            "sector": meta.sector,
            "price_band_pct": meta.price_band_pct,
            "trades_count": trades_count,
            "bid_ask_spread_pct": meta.bid_ask_spread_pct,
            "safe": passes,
        }
        return passes, rejections, diagnostics


penny_surveillance = PennySurveillanceFilter()
