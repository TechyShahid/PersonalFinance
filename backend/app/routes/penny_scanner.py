"""
REST API Routes for Specialized Penny Stock Swing Scanner.
Endpoint: GET /api/v1/scanner/penny-swing
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PennySwingCandidateResponse
from app.services.penny_scanner import run_penny_swing_scan

router = APIRouter(prefix="/api/v1/scanner", tags=["Penny Stock Swing Scanner"])


@router.get("/penny-swing", response_model=List[PennySwingCandidateResponse])
def get_penny_swing_candidates(
    exchange: str = Query(default="all", description="Exchange filter: all | NSE | BSE"),
    setup: str = Query(default="all", description="Setup filter: all | quiet_base | reversal"),
    min_turnover_cr: float = Query(default=2.5, ge=0.0, description="Minimum daily turnover in ₹ Crores (Liquidity Gate)"),
    max_operator_risk: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Filter candidates by max operator risk score (0-100)"),
    db: Session = Depends(get_db),
):
    """
    Specialized Penny Stock Swing Screening endpoint for Indian Equities (NSE/BSE).
    Enforces:
    - Price Boundary: ₹5.00 to ₹50.00
    - Market Cap: < ₹500 Crore
    - Circuit Limit: 10% or 20% price bands strictly required (2% and 5% discarded)
    - Regulatory Exclusions: ASM, GSM Stage 1-4, ESM Stage 1-2 filtered out
    - Liquidity Gates: Turnover >= ₹2.5 Cr, Unique Trades >= 2,500, Bid-Ask Spread <= 0.8%
    - Operator Risk Score (0-100) and Dynamic Liquidity-Constrained Position Sizing
    """
    candidates = run_penny_swing_scan(
        db=db,
        exchange_filter=exchange,
        setup_filter=setup,
        min_turnover_cr=min_turnover_cr,
        max_operator_risk=max_operator_risk,
    )
    return candidates
