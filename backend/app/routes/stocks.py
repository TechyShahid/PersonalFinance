"""
Stocks API Routes.
Provides searching, filtering, and summary metrics for all listed companies
ingested from the SEBI market capitalization classification universe.
"""

from typing import List, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models import Stock
from app.schemas import StockResponse

router = APIRouter(prefix="/api/stocks", tags=["Stocks Universe"])


@router.get("", response_model=dict)
def get_stocks(
    search: Optional[str] = Query(default=None, description="Search by symbol, company name, or ISIN"),
    category: Optional[str] = Query(default=None, description="Filter by category ('Large Cap', 'Mid Cap', 'Small Cap')"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List and search listed stocks with pagination and category filtering."""
    query = db.query(Stock)

    if category:
        # Case-insensitive or normalized category match
        query = query.filter(Stock.category.ilike(f"%{category.strip()}%"))

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Stock.company_name.ilike(search_pattern),
                Stock.nse_symbol.ilike(search_pattern),
                Stock.bse_symbol.ilike(search_pattern),
                Stock.isin.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(Stock.sr_no.asc()).offset((page - 1) * limit).limit(limit).all()
    pages = math.ceil(total / limit) if limit > 0 else 1

    return {
        "items": [StockResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit,
    }


@router.get("/summary", response_model=dict)
def get_stocks_summary(db: Session = Depends(get_db)):
    """Summary statistics of the listed stocks universe."""
    total = db.query(Stock).count()
    category_counts = {}
    for cat, cnt in db.query(Stock.category, func.count(Stock.id)).group_by(Stock.category).all():
        category_counts[cat or "Uncategorized"] = cnt

    nse_count = db.query(Stock).filter(Stock.nse_symbol.isnot(None)).count()
    bse_count = db.query(Stock).filter(Stock.bse_symbol.isnot(None)).count()
    msei_count = db.query(Stock).filter(Stock.msei_symbol.isnot(None)).count()

    return {
        "total_stocks": total,
        "categories": category_counts,
        "exchanges": {
            "nse_listed": nse_count,
            "bse_listed": bse_count,
            "msei_listed": msei_count,
        },
    }


from app.services.candle_service import get_stock_candles


@router.get("/{symbol}/candles", response_model=dict)
def get_candles(
    symbol: str,
    exchange: str = Query(default="NSE", description="Exchange (NSE or BSE)"),
    period: str = Query(default="1y", description="Timeframe period (1mo, 3mo, 6mo, 1y, 2y, 5y, max)"),
    interval: str = Query(default="1d", description="Candle interval (1d, 1wk, 1mo)"),
    refresh: bool = Query(default=False, description="Force refresh cache"),
):
    """Retrieve OHLCV candlestick data with technical indicators (EMA 20, EMA 50, RSI 14)."""
    return get_stock_candles(symbol=symbol, exchange=exchange, period=period, interval=interval, force_refresh=refresh)


@router.get("/{identifier}", response_model=StockResponse)
def get_stock_by_identifier(identifier: str, db: Session = Depends(get_db)):
    """Retrieve stock details by NSE symbol, BSE symbol, or ISIN."""
    clean_id = identifier.strip().upper()
    stock = (
        db.query(Stock)
        .filter(
            or_(
                Stock.nse_symbol == clean_id,
                Stock.bse_symbol == clean_id,
                Stock.isin == clean_id,
            )
        )
        .first()
    )
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{identifier}' not found in listed universe")
    return StockResponse.model_validate(stock)
