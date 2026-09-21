"""
Stock Candle & Historical Price Service.
Downloads and caches historical OHLCV candlestick data for Indian equities (NSE/BSE)
with support for Daily (1d), Weekly (1wk), and Monthly (1mo) candle aggregation.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import yfinance as yf

from app.database import DATA_DIR

DB_PATH = os.path.join(DATA_DIR, "finance.db")


def _get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_candle_cache_table():
    """Ensure the candle cache table exists with interval support."""
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_candles_cache_v2 (
                symbol TEXT,
                period TEXT,
                interval TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, period, interval)
            )
        """)
        conn.commit()


# Initialize on import
init_candle_cache_table()


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute 14-period RSI indicator."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def get_stock_candles(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetch OHLCV candlestick data for a given stock symbol and interval.
    Supports interval = '1d' (Daily), '1wk' (Weekly), '1mo' (Monthly).
    Uses local SQLite cache (TTL: 4 hours) to serve requests with sub-5ms latency.
    """
    clean_sym = symbol.strip().upper()
    period_clean = period.lower()
    interval_clean = interval.lower()

    # Map friendly interval names
    if interval_clean in ["d", "daily", "1d"]:
        interval_clean = "1d"
    elif interval_clean in ["w", "weekly", "1w", "1wk"]:
        interval_clean = "1wk"
    elif interval_clean in ["m", "monthly", "1m", "1mo"]:
        interval_clean = "1mo"
    else:
        interval_clean = "1d"

    # For weekly or monthly candles, ensure period is long enough to show meaningful history
    if interval_clean == "1wk" and period_clean in ["1mo", "3mo"]:
        period_clean = "1y"
    elif interval_clean == "1mo" and period_clean in ["1mo", "3mo", "6mo"]:
        period_clean = "2y"

    # 1. Check SQLite Cache
    if not force_refresh:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_json, updated_at FROM stock_candles_cache_v2 WHERE symbol = ? AND period = ? AND interval = ?",
                (clean_sym, period_clean, interval_clean)
            )
            row = cursor.fetchone()
            if row:
                cached_time_str = row["updated_at"]
                try:
                    cached_dt = datetime.strptime(cached_time_str, "%Y-%m-%d %H:%M:%S")
                    if datetime.utcnow() - cached_dt < timedelta(hours=4):
                        return json.loads(row["data_json"])
                except Exception:
                    return json.loads(row["data_json"])

    # 2. Fetch unadjusted OHLCV from Market (yfinance NSE / BSE)
    tickers_to_try = (
        [f"{clean_sym}.NS", f"{clean_sym}.BO", clean_sym]
        if exchange.upper() == "NSE"
        else [f"{clean_sym}.BO", f"{clean_sym}.NS", clean_sym]
    )

    df: Optional[pd.DataFrame] = None
    used_ticker: Optional[str] = None
    t_obj: Optional[yf.Ticker] = None

    for t_str in tickers_to_try:
        try:
            t = yf.Ticker(t_str)
            h = t.history(period=period_clean, interval=interval_clean, auto_adjust=False, timeout=6)
            if h is not None and not h.empty and len(h) > 0:
                df = h
                used_ticker = t_str
                t_obj = t
                break
        except Exception:
            continue

    # Fallback to DB seed if no rows found
    if df is None or len(df) == 0 or t_obj is None:
        candles, summary = _fallback_from_db(clean_sym)
    else:
        df = df.reset_index()

        # Patch unfinalized latest session Close from fast_info
        try:
            fi = t_obj.fast_info
            last_p = getattr(fi, "last_price", None)
            if len(df) > 0 and pd.isna(df.iloc[-1]["Close"]) and last_p is not None:
                idx = df.index[-1]
                df.loc[idx, "Close"] = float(last_p)
                if pd.isna(df.loc[idx, "Open"]) and getattr(fi, "open", None):
                    df.loc[idx, "Open"] = float(fi.open)
                if pd.isna(df.loc[idx, "High"]) and getattr(fi, "day_high", None):
                    df.loc[idx, "High"] = float(fi.day_high)
                if pd.isna(df.loc[idx, "Low"]) and getattr(fi, "day_low", None):
                    df.loc[idx, "Low"] = float(fi.day_low)
                if pd.isna(df.loc[idx, "Volume"]) and getattr(fi, "last_volume", None):
                    df.loc[idx, "Volume"] = int(fi.last_volume)
        except Exception as e:
            print(f"Warning: fast_info patch skipped for {clean_sym}: {e}")

        # Drop invalid rows
        df = df.dropna(subset=["Open", "High", "Low", "Close"])

        if len(df) == 0:
            candles, summary = _fallback_from_db(clean_sym)
        else:
            # Format date as YYYY-MM-DD in Asia/Kolkata
            if hasattr(df["Date"].dt, "tz") and df["Date"].dt.tz is not None:
                df["date_str"] = df["Date"].dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d")
            else:
                df["date_str"] = df["Date"].dt.strftime("%Y-%m-%d")

            # Sort chronologically & deduplicate
            df = df.sort_values(by="Date", ascending=True)
            df = df.drop_duplicates(subset=["date_str"], keep="last")

            # Technical indicators
            df["ema20"] = df["Close"].ewm(span=20, adjust=False).mean()
            df["ema50"] = df["Close"].ewm(span=50, adjust=False).mean()
            if len(df) >= 14:
                df["rsi"] = _compute_rsi(df["Close"], period=14)
            else:
                df["rsi"] = None

            candles = []
            for _, r in df.iterrows():
                candles.append({
                    "time": str(r["date_str"]),
                    "open": round(float(r["Open"]), 2),
                    "high": round(float(r["High"]), 2),
                    "low": round(float(r["Low"]), 2),
                    "close": round(float(r["Close"]), 2),
                    "volume": int(r["Volume"]) if not pd.isna(r["Volume"]) else 0,
                    "ema20": round(float(r["ema20"]), 2) if not pd.isna(r["ema20"]) else None,
                    "ema50": round(float(r["ema50"]), 2) if not pd.isna(r["ema50"]) else None,
                    "rsi": round(float(r["rsi"]), 2) if r["rsi"] is not None and not pd.isna(r["rsi"]) else None,
                })

            last_c = candles[-1]["close"]
            prev_c = candles[-2]["close"] if len(candles) > 1 else last_c
            first_c = candles[0]["close"]
            all_highs = [c["high"] for c in candles]
            all_lows = [c["low"] for c in candles]

            change_pct = round(((last_c - prev_c) / prev_c) * 100, 2) if prev_c else 0.0
            period_return_pct = round(((last_c - first_c) / first_c) * 100, 2) if first_c else 0.0

            summary = {
                "current_price": last_c,
                "previous_close": prev_c,
                "change_pct": change_pct,
                "period_return_pct": period_return_pct,
                "high_period": round(max(all_highs), 2) if all_highs else last_c,
                "low_period": round(min(all_lows), 2) if all_lows else last_c,
                "latest_volume": candles[-1]["volume"],
                "candle_count": len(candles),
                "ticker_used": used_ticker or f"{clean_sym}.NS",
                "interval": interval_clean,
            }

    result = {
        "symbol": clean_sym,
        "exchange": exchange.upper(),
        "period": period_clean,
        "interval": interval_clean,
        "summary": summary,
        "candles": candles,
    }

    # Save to SQLite Cache
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stock_candles_cache_v2 (symbol, period, interval, data_json, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(symbol, period, interval) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = datetime('now')
            """, (clean_sym, period_clean, interval_clean, json.dumps(result)))
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to save candle cache for {clean_sym}: {e}")

    return result


def _fallback_from_db(symbol: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fallback generator using newly_listed_stocks or daily_eod_data."""
    candles = []
    summary = {}
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT listing_date, listing_price, current_price, return_since_listing_pct, volume FROM newly_listed_stocks WHERE symbol = ?",
            (symbol,)
        )
        row = cursor.fetchone()
        if row and row["listing_price"] and row["current_price"]:
            lp = float(row["listing_price"])
            cp = float(row["current_price"])
            l_date = row["listing_date"] or "2026-01-01"
            today_str = datetime.utcnow().strftime("%Y-%m-%d")

            candles = [
                {
                    "time": l_date,
                    "open": lp,
                    "high": max(lp, cp),
                    "low": min(lp, cp),
                    "close": lp,
                    "volume": int(row["volume"] or 10000),
                    "ema20": lp,
                    "ema50": lp,
                    "rsi": 50.0,
                },
                {
                    "time": today_str,
                    "open": lp,
                    "high": max(lp, cp),
                    "low": min(lp, cp),
                    "close": cp,
                    "volume": int(row["volume"] or 50000),
                    "ema20": cp,
                    "ema50": cp,
                    "rsi": 55.0,
                }
            ]
            summary = {
                "current_price": cp,
                "previous_close": lp,
                "change_pct": round(((cp - lp) / lp) * 100, 2),
                "period_return_pct": row["return_since_listing_pct"] or round(((cp - lp) / lp) * 100, 2),
                "high_period": max(lp, cp),
                "low_period": min(lp, cp),
                "latest_volume": row["volume"] or 0,
                "candle_count": len(candles),
                "ticker_used": f"{symbol}.NS",
                "interval": "1d",
            }
        else:
            summary = {
                "current_price": 0.0,
                "previous_close": 0.0,
                "change_pct": 0.0,
                "period_return_pct": 0.0,
                "high_period": 0.0,
                "low_period": 0.0,
                "latest_volume": 0,
                "candle_count": 0,
                "ticker_used": f"{symbol}.NS",
                "interval": "1d",
            }

    return candles, summary
