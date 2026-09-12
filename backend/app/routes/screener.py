"""
Screener API Routes.
Swing trade candidate retrieval and manual screening triggers.
"""

from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ScreeningResult, DailyEodData
from app.schemas import ScreeningCandidateResponse, EodDataResponse
from app.services.screener import run_screening, get_screening_results

router = APIRouter(prefix="/api/screener", tags=["Screener"])


@router.get("/candidates", response_model=List[ScreeningCandidateResponse])
def get_candidates(
    min_score: float = Query(default=0, ge=0, le=100),
    setup_type: Optional[str] = Query(default=None),
    cap_category: Optional[str] = Query(default="MID_SMALL"),  # MID_SMALL | SMALLCAP | MIDCAP | LARGECAP | ALL
    sort_by: str = Query(default="score"),
    db: Session = Depends(get_db),
):
    """Get today's screened swing candidates, supporting Smallcap & Midcap filtering."""
    today = date.today()
    results = get_screening_results(
        db, scan_date=today, min_score=min_score, setup_type=setup_type, cap_category=cap_category
    )

    if not results:
        # Try yesterday if today's scan hasn't run
        yesterday = today - timedelta(days=1)
        results = get_screening_results(
            db, scan_date=yesterday, min_score=min_score, setup_type=setup_type, cap_category=cap_category
        )

    # If still no results, try the most recent scan date
    if not results:
        results = get_screening_results(
            db, min_score=min_score, setup_type=setup_type, cap_category=cap_category
        )

    # Sort
    if sort_by == "turnover":
        results.sort(key=lambda r: r.turnover_cr or 0, reverse=True)
    elif sort_by == "delivery":
        results.sort(key=lambda r: r.delivery_pct or 0, reverse=True)
    # Default is by score (already sorted)

    return results


@router.get("/history", response_model=List[ScreeningCandidateResponse])
def get_history(
    days: int = Query(default=30, ge=1, le=90),
    symbol: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get historical screening results."""
    cutoff = date.today() - timedelta(days=days)
    query = db.query(ScreeningResult).filter(ScreeningResult.scan_date >= cutoff)

    if symbol:
        query = query.filter(ScreeningResult.symbol == symbol.upper())

    return query.order_by(ScreeningResult.scan_date.desc()).limit(100).all()


@router.post("/run", response_model=List[ScreeningCandidateResponse])
def trigger_screening(db: Session = Depends(get_db)):
    """Trigger a manual screening run for today."""
    results = run_screening(db, scan_date=date.today())
    return results


@router.get("/sparkline/{symbol}", response_model=List[EodDataResponse])
def get_sparkline_data(
    symbol: str,
    days: int = Query(default=20, ge=5, le=60),
    db: Session = Depends(get_db),
):
    """Get recent price data for sparkline charts."""
    cutoff = date.today() - timedelta(days=int(days * 1.5))
    rows = (
        db.query(DailyEodData)
        .filter(
            DailyEodData.symbol == symbol.upper(),
            DailyEodData.trade_date >= cutoff,
        )
        .order_by(DailyEodData.trade_date.asc())
        .limit(days)
        .all()
    )
    return rows
