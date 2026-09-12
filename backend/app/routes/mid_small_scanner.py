"""
REST API Routes for Specialized Smallcap & Midcap Swing Scanner.
Endpoint: GET /api/v1/scanner/mid-small-swing
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import MidSmallSwingCandidateResponse
from app.services.mid_small_scanner import run_mid_small_swing_scan

router = APIRouter(prefix="/api/v1/scanner", tags=["Smallcap & Midcap Swing Scanner"])


@router.get("/mid-small-swing", response_model=List[MidSmallSwingCandidateResponse])
def get_mid_small_swing_candidates(
    cap_type: str = Query(default="all", description="Market cap filter: all | midcap | smallcap"),
    setup: str = Query(default="all", description="Setup filter: all | vcp | pullback | breakout"),
    min_turnover_cr: float = Query(default=10.0, ge=0.0, description="Minimum daily turnover in ₹ Crores"),
    db: Session = Depends(get_db),
):
    """
    Institutional screening endpoint for Nifty Midcap 150 and Smallcap 250 swing candidates.
    Applies strict series EQ validation, ASM/GSM surveillance filtering, Mansfield RS calculation,
    ADV >= 200,000 shares, and institutional delivery footprint gates.
    """
    candidates = run_mid_small_swing_scan(
        db=db,
        cap_type=cap_type,
        setup_filter=setup,
        min_turnover_cr=min_turnover_cr,
    )
    return candidates
