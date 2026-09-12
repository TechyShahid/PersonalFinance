"""
EOD Data Ingestion Service.
Handles parsing of NSE Bhavcopy CSVs, computing technical indicators,
and maintaining the daily_eod_data table.

For the MVP, includes synthetic data generation for demo purposes.
"""

import math
from datetime import date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import DailyEodData, FiiDiiData


# ─── Technical Indicator Computation ────────────────────────────────────────────

def compute_ema(prices: List[float], period: int) -> List[Optional[float]]:
    """Compute Exponential Moving Average for a price series."""
    if len(prices) < period:
        return [None] * len(prices)

    ema_values: List[Optional[float]] = [None] * (period - 1)
    # Seed with SMA
    sma = sum(prices[:period]) / period
    ema_values.append(round(sma, 2))

    multiplier = 2.0 / (period + 1)
    for i in range(period, len(prices)):
        ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(round(ema, 2))

    return ema_values


def compute_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """Compute Average True Range."""
    if len(highs) < period + 1:
        return [None] * len(highs)

    true_ranges = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    atr_values: List[Optional[float]] = [None] * (period - 1)
    atr = sum(true_ranges[:period]) / period
    atr_values.append(round(atr, 2))

    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period
        atr_values.append(round(atr, 2))

    return atr_values


def compute_delivery_avg(deliveries: List[int], period: int = 20) -> List[Optional[float]]:
    """Compute rolling average of deliverable quantity."""
    result: List[Optional[float]] = []
    for i in range(len(deliveries)):
        if i < period - 1:
            result.append(None)
        else:
            avg = sum(deliveries[i - period + 1 : i + 1]) / period
            result.append(round(avg, 2))
    return result


def compute_volume_avg(volumes: List[int], period: int = 20) -> List[Optional[float]]:
    """Compute rolling average volume."""
    result: List[Optional[float]] = []
    for i in range(len(volumes)):
        if i < period - 1:
            result.append(None)
        else:
            avg = sum(volumes[i - period + 1 : i + 1]) / period
            result.append(round(avg, 2))
    return result


def compute_rolling_std(closes: List[float], period: int = 20) -> List[Optional[float]]:
    """Compute rolling standard deviation of closing prices."""
    result: List[Optional[float]] = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            result.append(round(math.sqrt(variance), 4))
    return result


# ─── Technicals Update ──────────────────────────────────────────────────────────

def update_technicals_for_symbol(db: Session, symbol: str) -> None:
    """Recompute and store EMA-20, EMA-50, ATR-14 for a symbol's full history."""
    rows = (
        db.query(DailyEodData)
        .filter(DailyEodData.symbol == symbol)
        .order_by(DailyEodData.trade_date.asc())
        .all()
    )
    if not rows:
        return

    closes = [r.close_price for r in rows]
    highs = [r.high_price for r in rows]
    lows = [r.low_price for r in rows]

    ema_20_vals = compute_ema(closes, 20)
    ema_50_vals = compute_ema(closes, 50)
    atr_14_vals = compute_atr(highs, lows, closes, 14)

    for i, row in enumerate(rows):
        row.ema_20 = ema_20_vals[i]
        row.ema_50 = ema_50_vals[i]
        row.atr_14 = atr_14_vals[i]

    db.commit()


def update_all_technicals(db: Session) -> None:
    """Recompute technicals for all symbols in the database."""
    symbols = db.query(DailyEodData.symbol).distinct().all()
    for (symbol,) in symbols:
        update_technicals_for_symbol(db, symbol)


# ─── Bhavcopy Parsing (Production-ready, uses synthetic data for MVP) ────────

def parse_bhavcopy_row(row: Dict) -> Optional[Dict]:
    """
    Parse a single row from NSE Bhavcopy CSV.
    Expected columns: SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, LAST,
    PREVCLOSE, TOTTRDQTY, TOTTRDVAL, TIMESTAMP, TOTALTRADES,
    ISIN, DELIVERYQTY, DELIVERYPERCENTAGE
    """
    if row.get("SERIES", "").strip() != "EQ":
        return None

    try:
        total_traded_val = float(row.get("TOTTRDVAL", 0))
        turnover_cr = total_traded_val / 1e7  # Convert to crores

        return {
            "symbol": row["SYMBOL"].strip(),
            "series": "EQ",
            "open_price": float(row.get("OPEN", 0)),
            "high_price": float(row.get("HIGH", 0)),
            "low_price": float(row.get("LOW", 0)),
            "close_price": float(row.get("CLOSE", 0)),
            "last_price": float(row.get("LAST", 0)),
            "prev_close": float(row.get("PREVCLOSE", 0)),
            "total_traded_qty": int(row.get("TOTTRDQTY", 0)),
            "total_traded_value": total_traded_val,
            "deliverable_qty": int(row.get("DELIVERYQTY", 0) or 0),
            "delivery_pct": float(row.get("DELIVERYPERCENTAGE", 0) or 0),
            "turnover_cr": round(turnover_cr, 2),
        }
    except (KeyError, ValueError):
        return None


def ingest_eod_batch(db: Session, records: List[Dict], trade_date: date) -> int:
    """Insert a batch of parsed EOD records into the database."""
    inserted = 0
    for rec in records:
        existing = (
            db.query(DailyEodData)
            .filter(
                DailyEodData.symbol == rec["symbol"],
                DailyEodData.trade_date == trade_date,
            )
            .first()
        )
        if existing:
            continue

        eod = DailyEodData(trade_date=trade_date, **rec)
        db.add(eod)
        inserted += 1

    db.commit()
    return inserted


def get_symbol_history(
    db: Session, symbol: str, days: int = 120
) -> List[DailyEodData]:
    """Fetch historical EOD data for a symbol."""
    cutoff = date.today() - timedelta(days=days)
    return (
        db.query(DailyEodData)
        .filter(DailyEodData.symbol == symbol, DailyEodData.trade_date >= cutoff)
        .order_by(DailyEodData.trade_date.asc())
        .all()
    )


def get_latest_eod(db: Session, symbol: str) -> Optional[DailyEodData]:
    """Get the most recent EOD data for a symbol."""
    return (
        db.query(DailyEodData)
        .filter(DailyEodData.symbol == symbol)
        .order_by(DailyEodData.trade_date.desc())
        .first()
    )


def get_all_symbols(db: Session) -> List[str]:
    """Get all distinct symbols in the database."""
    results = db.query(DailyEodData.symbol).distinct().all()
    return [r[0] for r in results]
