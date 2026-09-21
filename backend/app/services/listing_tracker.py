"""
Listing Tracker Service.
Tracks all stocks listed on NSE within the past 1 year (< 365 days),
computes genuine listing gains, current market prices, all-time highs,
and identifies top-performing IPOs/new listings (Outperformers).
"""

import os
import sys
import logging
import concurrent.futures
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import yfinance as yf
from nselib import capital_market
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import engine, SessionLocal, Base
from app.models import NewlyListedStock, Stock

logger = logging.getLogger(__name__)


def classify_performance_tier(return_pct: Optional[float]) -> str:
    """Classify return since listing into distinct qualitative tiers."""
    if return_pct is None:
        return "NEUTRAL"
    if return_pct >= 100.0:
        return "MULTIBAGGER"
    if return_pct >= 50.0:
        return "HIGH_FLYER"
    if return_pct >= 20.0:
        return "OUTPERFORMER"
    if return_pct >= 0.0:
        return "NEUTRAL"
    return "LAGGARD"


def sync_newly_listed_stocks(db: Session, force_reload: bool = False) -> Dict[str, Any]:
    """
    Ingest and sync all equities listed on NSE in the past 1 year (365 days).
    Computes listing prices, current prices, total return since listing,
    and identifies the top outperforming stocks.
    """
    # Ensure table exists
    Base.metadata.create_all(bind=engine)

    existing_count = db.query(NewlyListedStock).count()
    if existing_count > 0 and not force_reload:
        outperformers_count = db.query(NewlyListedStock).filter(NewlyListedStock.is_outperformer == True).count()
        return {
            "status": "already_loaded",
            "total_listings": existing_count,
            "outperformers_count": outperformers_count,
            "message": f"Table 'newly_listed_stocks' already contains {existing_count} records."
        }

    print("🚀 Fetching official NSE equity listing records...")
    try:
        eq = capital_market.equity_list()
        eq.columns = [c.strip() for c in eq.columns]
        eq["LISTING_DATE"] = pd.to_datetime(eq["DATE OF LISTING"], format="%d-%b-%Y", errors="coerce")
    except Exception as e:
        print(f"  ⚠️ Error fetching equity_list: {e}")
        return {"status": "error", "message": str(e)}

    # Determine 1-year cutoff window (365 days)
    max_date = eq["LISTING_DATE"].max()
    if pd.isna(max_date):
        max_date = pd.Timestamp.now()
    cutoff_date = max_date - pd.Timedelta(days=365)

    recent_eq = eq[eq["LISTING_DATE"] >= cutoff_date].copy()
    print(f"  ✓ Found {len(recent_eq)} equities listed in the past 1 year (since {cutoff_date.date()}).")

    # Fetch latest Bhavcopy for delivery & latest volume/prices
    bhav_dict = {}
    try:
        bhav = capital_market.bhav_copy_with_delivery("11-09-2026")
        if bhav is not None and not bhav.empty:
            bhav = bhav[bhav["SERIES"] == "EQ"].copy()
            bhav["SYMBOL"] = bhav["SYMBOL"].str.strip()
            for _, r in bhav.iterrows():
                bhav_dict[r["SYMBOL"]] = {
                    "close": float(r.get("CLOSE_PRICE", 0) or 0),
                    "prev_close": float(r.get("PREV_CLOSE", 0) or 0),
                    "turnover_cr": round(float(r.get("TURNOVER_LACS", 0) or 0) / 100.0, 2),
                    "volume": int(r.get("TTL_TRD_QNTY", 0) or 0),
                    "deliv_pct": float(r.get("DELIV_PER", 0) or 0) if pd.notna(r.get("DELIV_PER")) else 0.0,
                }
            print(f"  ✓ Bhavcopy mapped for {len(bhav_dict)} symbols.")
    except Exception as e:
        print(f"  ⚠️ Note on Bhavcopy fetch: {e}")

    # Load market cap & category mapping from stocks table
    stock_cache = {}
    for s in db.query(Stock).filter(Stock.nse_symbol.isnot(None)).all():
        stock_cache[s.nse_symbol] = {
            "category": s.category or "Small Cap",
            "mcap_cr": s.avg_mcap_cr or s.nse_mcap_cr or 500.0,
        }

    # Fetch historical price metrics via yfinance in batches for fast, accurate calculation
    symbols = recent_eq["SYMBOL"].tolist()
    ticker_symbols = [f"{s}.NS" for s in symbols]

    print(f"📥 Downloading price history for {len(symbols)} newly listed stocks...")
    price_metrics = {}
    try:
        # Download in chunked batches
        batch_size = 60
        for i in range(0, len(ticker_symbols), batch_size):
            chunk = ticker_symbols[i : i + batch_size]
            data = yf.download(chunk, period="1y", group_by="ticker", progress=False)
            for t in chunk:
                sym = t.replace(".NS", "")
                try:
                    if t in data.columns.levels[0]:
                        df_s = data[t].dropna()
                        if not df_s.empty:
                            first_close = round(float(df_s.iloc[0]["Close"]), 2)
                            last_close = round(float(df_s.iloc[-1]["Close"]), 2)
                            high_price = round(float(df_s["High"].max()), 2)
                            ret_pct = round(((last_close - first_close) / first_close) * 100.0, 2)
                            dd_pct = round(((last_close - high_price) / high_price) * 100.0, 2)
                            price_metrics[sym] = {
                                "listing_price": first_close,
                                "current_price": last_close,
                                "return_pct": ret_pct,
                                "high_price": high_price,
                                "drawdown_pct": dd_pct,
                            }
                except Exception:
                    pass
        print(f"  ✓ Processed history metrics for {len(price_metrics)} stocks.")
    except Exception as e:
        print(f"  ⚠️ Batch price fetch notice: {e}")

    # Set of known bulk BSE-to-NSE cross-listing dates where legacy companies were permitted to trade
    BULK_CROSS_LISTING_DATES = {date(2026, 8, 17), date(2026, 4, 20)}

    today_dt = date.today()
    cutoff_365 = today_dt - timedelta(days=365)
    records = []

    for _, row in recent_eq.iterrows():
        sym = str(row["SYMBOL"]).strip()
        comp_name = str(row["NAME OF COMPANY"]).strip()
        list_dt = row["LISTING_DATE"].date()
        days_on_market = max(1, (today_dt - list_dt).days)

        # Detect old legacy companies that were merely cross-listed / migrated from BSE
        is_relisted = (list_dt in BULK_CROSS_LISTING_DATES)
        listing_type = "RE_LISTED" if is_relisted else "FRESH_IPO"

        # Market cap info
        sc = stock_cache.get(sym, {})
        cat = sc.get("category", "Small Cap")
        mcap = sc.get("mcap_cr", None)

        # Bhavcopy info
        bhav_info = bhav_dict.get(sym, {})

        # Price info
        p_info = price_metrics.get(sym, {})
        listing_p = p_info.get("listing_price")
        curr_p = p_info.get("current_price") or bhav_info.get("close")
        ret_pct = p_info.get("return_pct")
        high_p = p_info.get("high_price") or curr_p
        dd_pct = p_info.get("drawdown_pct", 0.0)

        # Fallback if yfinance didn't return price
        if curr_p and not listing_p:
            prev_c = bhav_info.get("prev_close") or curr_p
            listing_p = prev_c
            ret_pct = round(((curr_p - listing_p) / listing_p) * 100.0, 2) if listing_p > 0 else 0.0

        if not curr_p and listing_p:
            curr_p = listing_p

        # 1-day change
        prev_p = bhav_info.get("prev_close")
        chg_pct = round(((curr_p - prev_p) / prev_p) * 100.0, 2) if prev_p and curr_p else 0.0

        # Only genuine fresh IPOs can be tagged as Outperformers to exclude old re-listed symbols
        is_outperformer = (not is_relisted) and (ret_pct is not None and ret_pct >= 20.0)

        rec = {
            "symbol": sym,
            "company_name": comp_name,
            "series": str(row.get("SERIES", "EQ")).strip(),
            "listing_date": list_dt,
            "days_since_listing": days_on_market,
            "category": cat,
            "market_cap_cr": mcap,
            "listing_price": listing_p,
            "current_price": curr_p,
            "change_pct": chg_pct,
            "return_since_listing_pct": ret_pct if ret_pct is not None else 0.0,
            "all_time_high": high_p,
            "drawdown_from_high_pct": dd_pct,
            "volume": bhav_info.get("volume", 0),
            "turnover_cr": bhav_info.get("turnover_cr", 0.0),
            "delivery_pct": bhav_info.get("deliv_pct", 0.0),
            "is_outperformer": is_outperformer,
            "is_relisted": is_relisted,
            "listing_type": listing_type,
        }
        records.append(rec)

    # Sort genuine fresh IPOs first by return descending to assign top performance ranks
    fresh_records = [r for r in records if not r["is_relisted"]]
    relisted_records = [r for r in records if r["is_relisted"]]

    fresh_records.sort(key=lambda x: x["return_since_listing_pct"], reverse=True)
    for idx, r in enumerate(fresh_records, 1):
        r["performance_rank"] = idx

    relisted_records.sort(key=lambda x: x["return_since_listing_pct"], reverse=True)
    for idx, r in enumerate(relisted_records, len(fresh_records) + 1):
        r["performance_rank"] = idx

    all_sorted_records = fresh_records + relisted_records

    print(f"Writing {len(all_sorted_records)} newly listed stocks ({len(fresh_records)} fresh IPOs, {len(relisted_records)} re-listed) to database...")
    db.query(NewlyListedStock).delete()
    db.commit()

    db.bulk_insert_mappings(NewlyListedStock, all_sorted_records)
    db.commit()

    total_count = db.query(NewlyListedStock).count()
    fresh_count = db.query(NewlyListedStock).filter(NewlyListedStock.is_relisted == False).count()
    outperformers_count = db.query(NewlyListedStock).filter(NewlyListedStock.is_outperformer == True).count()
    print(f"✅ Successfully loaded {total_count} newly listed stocks ({fresh_count} fresh IPOs, {outperformers_count} fresh outperformers).")

    return {
        "status": "success",
        "total_listings": total_count,
        "fresh_ipos_count": fresh_count,
        "relisted_count": total_count - fresh_count,
        "outperformers_count": outperformers_count,
        "message": f"Successfully loaded {total_count} stocks ({fresh_count} fresh IPOs)."
    }


def fetch_single_operating_profit(symbol: str):
    """Fetch annual Operating Income for a single ticker via yfinance."""
    try:
        t = yf.Ticker(f"{symbol}.NS")
        stmt = t.income_stmt
        if stmt is not None and not stmt.empty and "Operating Income" in stmt.index:
            vals = stmt.loc["Operating Income"].dropna()
            if len(vals) >= 2:
                cur, prev = float(vals.iloc[0]), float(vals.iloc[1])
                growth = round(((cur - prev) / abs(prev) * 100.0), 2) if prev != 0 else 0.0
                return symbol, round(cur / 1e7, 2), round(prev / 1e7, 2), growth, growth > 0
            elif len(vals) == 1:
                cur = float(vals.iloc[0])
                return symbol, round(cur / 1e7, 2), None, None, False
        return symbol, None, None, None, False
    except Exception:
        return symbol, None, None, None, False


def sync_operating_profits(db: Session, symbols: Optional[List[str]] = None, max_workers: int = 15) -> dict:
    """
    Fetch and update operating profit metrics (latest, previous, YoY growth %, is_op_profit_growing)
    for newly listed stocks in parallel.
    """
    query = db.query(NewlyListedStock)
    if symbols:
        query = query.filter(NewlyListedStock.symbol.in_(symbols))

    stocks_to_fetch = [s.symbol for s in query.all()]
    if not stocks_to_fetch:
        return {"updated": 0, "growing_count": 0}

    print(f"📈 Fetching annual operating profit data for {len(stocks_to_fetch)} stocks in parallel...")
    updated_count = 0
    growing_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(fetch_single_operating_profit, stocks_to_fetch))

    for sym, cur_cr, prev_cr, growth, is_growing in results:
        stock = db.query(NewlyListedStock).filter(NewlyListedStock.symbol == sym).first()
        if stock:
            stock.operating_profit_cr = cur_cr
            stock.prev_operating_profit_cr = prev_cr
            stock.operating_profit_growth_pct = growth
            stock.is_op_profit_growing = bool(is_growing)
            updated_count += 1
            if is_growing:
                growing_count += 1

    db.commit()
    print(f"  ✓ Updated operating profit for {updated_count} stocks ({growing_count} with YoY growth).")
    return {"updated": updated_count, "growing_count": growing_count}


def get_newly_listed_stats(db: Session) -> Dict[str, Any]:
    """Get high-level summary statistics for New Listings Tracker, focused on genuine fresh IPOs."""
    total = db.query(NewlyListedStock).count()
    if total == 0:
        return {
            "total_listings": 0,
            "fresh_ipos_count": 0,
            "relisted_count": 0,
            "outperformers_count": 0,
            "outperformers_pct": 0.0,
            "median_return_pct": 0.0,
            "average_return_pct": 0.0,
            "op_profit_growing_count": 0,
            "op_profit_growing_pct": 0.0,
            "top_performer": None,
            "category_breakdown": {},
        }

    fresh_total = db.query(NewlyListedStock).filter(NewlyListedStock.is_relisted == False).count()
    relisted_total = total - fresh_total

    outperformers = db.query(NewlyListedStock).filter(NewlyListedStock.is_outperformer == True).count()
    outperformers_pct = round((outperformers / fresh_total) * 100.0, 1) if fresh_total > 0 else 0.0

    # Calculate statistics focused on genuine fresh IPOs
    fresh_returns = [
        r[0] for r in db.query(NewlyListedStock.return_since_listing_pct)
        .filter(NewlyListedStock.is_relisted == False).all() if r[0] is not None
    ]
    median_ret = round(float(np.median(fresh_returns)), 2) if fresh_returns else 0.0
    avg_ret = round(float(np.mean(fresh_returns)), 2) if fresh_returns else 0.0

    # Operating profit growing count among fresh IPOs
    op_growing_count = (
        db.query(NewlyListedStock)
        .filter(NewlyListedStock.is_relisted == False, NewlyListedStock.is_op_profit_growing == True)
        .count()
    )
    op_growing_pct = round((op_growing_count / fresh_total) * 100.0, 1) if fresh_total > 0 else 0.0

    # Top performer among genuine fresh IPOs
    top_stock = (
        db.query(NewlyListedStock)
        .filter(NewlyListedStock.is_relisted == False)
        .order_by(desc(NewlyListedStock.return_since_listing_pct))
        .first()
    )
    top_performer = None
    if top_stock:
        top_performer = {
            "symbol": top_stock.symbol,
            "company_name": top_stock.company_name,
            "return_pct": top_stock.return_since_listing_pct,
            "current_price": top_stock.current_price,
            "listing_date": top_stock.listing_date.isoformat(),
        }

    cats = {}
    for c, cnt in (
        db.query(NewlyListedStock.category, func.count(NewlyListedStock.id))
        .filter(NewlyListedStock.is_relisted == False)
        .group_by(NewlyListedStock.category).all()
    ):
        cats[c or "Uncategorized"] = cnt

    return {
        "total_listings": total,
        "fresh_ipos_count": fresh_total,
        "relisted_count": relisted_total,
        "outperformers_count": outperformers,
        "outperformers_pct": outperformers_pct,
        "median_return_pct": median_ret,
        "average_return_pct": avg_ret,
        "op_profit_growing_count": op_growing_count,
        "op_profit_growing_pct": op_growing_pct,
        "top_performer": top_performer,
        "category_breakdown": cats,
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = sync_newly_listed_stocks(db, force_reload="--force" in sys.argv)
        print("Sync result:", res)
        stats = get_newly_listed_stats(db)
        print("Stats:", stats)
    finally:
        db.close()
