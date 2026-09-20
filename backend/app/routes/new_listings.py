"""
New Listings & IPO Tracker API Routes.
Provides two primary views:
1. Section 1: All equities listed within the past 1 year (< 365 days).
2. Section 2: Top-performing newly listed stocks ("Outperformers" / Momentum Leaders).
"""

from datetime import date, timedelta
from typing import List, Optional
import math
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.database import get_db
from app.models import NewlyListedStock
from app.schemas import NewlyListedStockResponse, NewListingsStatsResponse
from app.services.listing_tracker import get_newly_listed_stats, sync_newly_listed_stocks, classify_performance_tier

router = APIRouter(prefix="/api/new-listings", tags=["New Listings Tracker"])


def enrich_stock_response(stock: NewlyListedStock) -> NewlyListedStockResponse:
    """Add computed performance tier badge to the stock response."""
    res = NewlyListedStockResponse.model_validate(stock)
    res.performance_tier = classify_performance_tier(stock.return_since_listing_pct)
    return res


@router.get("", response_model=dict)
def get_all_new_listings(
    search: Optional[str] = Query(default=None, description="Search by symbol or company name"),
    category: Optional[str] = Query(default=None, description="Filter by cap category (Large Cap, Mid Cap, Small Cap)"),
    timeframe_days: Optional[int] = Query(default=365, description="Max listing age in days (30, 90, 180, 365)"),
    min_return: Optional[float] = Query(default=None, description="Filter by minimum return since listing %"),
    only_fresh_ipos: bool = Query(default=True, description="Filter out old re-listed symbols and show only genuine fresh IPOs"),
    listing_type: Optional[str] = Query(default=None, description="'FRESH_IPO' | 'RE_LISTED' | 'ALL'"),
    sort_by: str = Query(default="listing_date", description="Sort field: listing_date, return_pct, mcap, price, change"),
    order: str = Query(default="desc", description="Sort direction: asc or desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    SECTION 1: Retrieve all newly listed stocks within the past 1 year (or filtered timeframe)
    with search, category, fresh IPO filtering, and flexible sorting.
    """
    query = db.query(NewlyListedStock)

    # Filter out old re-listed stocks if requested (default: True)
    if listing_type and listing_type.upper() != "ALL":
        if listing_type.upper() == "FRESH_IPO":
            query = query.filter(NewlyListedStock.is_relisted == False)
        elif listing_type.upper() == "RE_LISTED":
            query = query.filter(NewlyListedStock.is_relisted == True)
    elif only_fresh_ipos:
        query = query.filter(NewlyListedStock.is_relisted == False)

    # Timeframe filter
    if timeframe_days and timeframe_days > 0:
        cutoff = date.today() - timedelta(days=timeframe_days)
        query = query.filter(NewlyListedStock.listing_date >= cutoff)

    # Cap category filter
    if category and category.lower() != "all":
        query = query.filter(NewlyListedStock.category.ilike(f"%{category.strip()}%"))

    # Search query
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                NewlyListedStock.symbol.ilike(pattern),
                NewlyListedStock.company_name.ilike(pattern),
            )
        )

    # Min return filter
    if min_return is not None:
        query = query.filter(NewlyListedStock.return_since_listing_pct >= min_return)

    # Sorting
    sort_column_map = {
        "listing_date": NewlyListedStock.listing_date,
        "return_pct": NewlyListedStock.return_since_listing_pct,
        "mcap": NewlyListedStock.market_cap_cr,
        "price": NewlyListedStock.current_price,
        "change": NewlyListedStock.change_pct,
        "rank": NewlyListedStock.performance_rank,
    }
    sort_col = sort_column_map.get(sort_by, NewlyListedStock.listing_date)
    query = query.order_by(desc(sort_col) if order.lower() == "desc" else asc(sort_col))

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    pages = math.ceil(total / limit) if limit > 0 else 1

    return {
        "items": [enrich_stock_response(item) for item in items],
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit,
    }


@router.get("/outperformers", response_model=List[NewlyListedStockResponse])
def get_outperforming_listings(
    tier: Optional[str] = Query(default=None, description="Tier filter: MULTIBAGGER (>100%), HIGH_FLYER (>50%), OUTPERFORMER (>20%), ALL"),
    include_relisted: bool = Query(default=False, description="Whether to include old re-listed legacy stocks"),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    SECTION 2: Retrieve the top performing newly listed stocks (Outperformers)
    ranked strictly by return since listing %. Filters out old re-listed stocks by default.
    """
    query = db.query(NewlyListedStock).filter(NewlyListedStock.is_outperformer == True)

    if not include_relisted:
        query = query.filter(NewlyListedStock.is_relisted == False)

    if tier and tier.upper() != "ALL":
        t = tier.upper()
        if t == "MULTIBAGGER":
            query = query.filter(NewlyListedStock.return_since_listing_pct >= 100.0)
        elif t == "HIGH_FLYER":
            query = query.filter(NewlyListedStock.return_since_listing_pct >= 50.0)
        elif t == "OUTPERFORMER":
            query = query.filter(NewlyListedStock.return_since_listing_pct >= 20.0)

    # Sort strictly by return since listing descending
    stocks = query.order_by(desc(NewlyListedStock.return_since_listing_pct)).limit(limit).all()
    return [enrich_stock_response(s) for s in stocks]


@router.get("/stats", response_model=NewListingsStatsResponse)
def get_tracker_stats(db: Session = Depends(get_db)):
    """Retrieve aggregate KPI stats for the top banner of the tracker."""
    stats = get_newly_listed_stats(db)
    return stats


def _background_sync():
    from app.database import SessionLocal
    bg_db = SessionLocal()
    try:
        sync_newly_listed_stocks(bg_db, force_reload=True)
    except Exception as e:
        print(f"Error in background sync: {e}")
    finally:
        bg_db.close()


@router.post("/refresh", response_model=dict)
def refresh_tracker_data(background_tasks: BackgroundTasks):
    """Trigger an on-demand re-sync of newly listed stocks in the background without blocking."""
    background_tasks.add_task(_background_sync)
    return {"status": "sync_started", "message": "Market data synchronization started in background."}

