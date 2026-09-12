"""
Dashboard API Routes.
Portfolio overview, performance curves, and FII/DII sentiment.
"""

from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Portfolio, Holding, TradeOrder, FiiDiiData, DailyEodData
from app.schemas import DashboardSummary, PerformanceResponse, PerformancePoint, FiiDiiResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get portfolio overview with key metrics."""
    user = db.query(User).first()
    if not user:
        return DashboardSummary(
            total_capital=0, core_deployed=0, core_cash=0,
            satellite_deployed=0, satellite_cash=0,
            total_unrealized_pnl=0, total_realized_pnl=0,
            active_swing_trades=0, max_concurrent_swings=6,
            todays_pnl=0, win_rate=0, total_trades=0,
        )

    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    core = next((p for p in portfolios if p.portfolio_type == "CORE"), None)
    satellite = next((p for p in portfolios if p.portfolio_type == "SATELLITE"), None)

    # Unrealized P&L from active holdings
    holdings = db.query(Holding).filter(Holding.status == "ACTIVE").all()
    total_unrealized = sum(h.unrealized_pnl or 0 for h in holdings)

    # Realized P&L from closed trades
    total_realized = (
        db.query(func.sum(TradeOrder.net_return))
        .filter(TradeOrder.user_id == user.id, TradeOrder.status == "TAX_RECORDED")
        .scalar() or 0
    )

    # Active swing trades
    active_swings = (
        db.query(TradeOrder)
        .filter(TradeOrder.user_id == user.id, TradeOrder.status == "OPEN")
        .count()
    )

    # Win rate
    closed_trades = (
        db.query(TradeOrder)
        .filter(
            TradeOrder.user_id == user.id,
            TradeOrder.status == "TAX_RECORDED",
        )
        .all()
    )
    total_trades = len(closed_trades)
    winning = sum(1 for t in closed_trades if (t.realized_pnl or 0) > 0)
    win_rate = round((winning / total_trades * 100) if total_trades > 0 else 0, 1)

    # Today's P&L (simplified: unrealized change)
    todays_pnl = round(total_unrealized * 0.02, 2)  # Approximation

    return DashboardSummary(
        total_capital=user.total_capital,
        core_deployed=core.deployed_capital if core else 0,
        core_cash=core.cash_available if core else 0,
        satellite_deployed=satellite.deployed_capital if satellite else 0,
        satellite_cash=satellite.cash_available if satellite else 0,
        total_unrealized_pnl=round(total_unrealized, 2),
        total_realized_pnl=round(total_realized, 2),
        active_swing_trades=active_swings,
        max_concurrent_swings=user.max_concurrent_swings,
        todays_pnl=todays_pnl,
        win_rate=win_rate,
        total_trades=total_trades,
    )


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(days: int = 90, db: Session = Depends(get_db)):
    """Get portfolio performance vs benchmarks over time."""
    import random

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Generate performance curve (synthetic for MVP)
    data_points = []
    portfolio_base = 2500000.0
    nifty_base = 100.0
    midcap_base = 100.0

    current_date = start_date
    portfolio_val = portfolio_base
    nifty_val = nifty_base
    midcap_val = midcap_base

    while current_date <= end_date:
        if current_date.weekday() < 5:  # Trading days
            portfolio_val *= (1 + random.gauss(0.0008, 0.012))
            nifty_val *= (1 + random.gauss(0.0005, 0.010))
            midcap_val *= (1 + random.gauss(0.0006, 0.013))

            data_points.append(PerformancePoint(
                date=current_date,
                portfolio_value=round(portfolio_val, 2),
                nifty_50_value=round(nifty_val, 2),
                nifty_midcap_150_value=round(midcap_val, 2),
            ))
        current_date += timedelta(days=1)

    portfolio_return = round(
        (data_points[-1].portfolio_value / portfolio_base - 1) * 100, 2
    ) if data_points else 0
    nifty_return = round(
        (data_points[-1].nifty_50_value / nifty_base - 1) * 100, 2
    ) if data_points else 0
    midcap_return = round(
        (data_points[-1].nifty_midcap_150_value / midcap_base - 1) * 100, 2
    ) if data_points else 0

    return PerformanceResponse(
        data=data_points,
        portfolio_return_pct=portfolio_return,
        nifty_50_return_pct=nifty_return,
        nifty_midcap_return_pct=midcap_return,
    )


@router.get("/fii-dii", response_model=List[FiiDiiResponse])
def get_fii_dii(days: int = 10, db: Session = Depends(get_db)):
    """Get recent FII/DII activity."""
    cutoff = date.today() - timedelta(days=days * 2)

    fii_data = (
        db.query(FiiDiiData)
        .filter(FiiDiiData.trade_date >= cutoff, FiiDiiData.participant_type == "FII")
        .order_by(FiiDiiData.trade_date.desc())
        .limit(days)
        .all()
    )

    dii_data = (
        db.query(FiiDiiData)
        .filter(FiiDiiData.trade_date >= cutoff, FiiDiiData.participant_type == "DII")
        .order_by(FiiDiiData.trade_date.desc())
        .limit(days)
        .all()
    )

    # Combine by date
    fii_by_date = {f.trade_date: f for f in fii_data}
    dii_by_date = {d.trade_date: d for d in dii_data}
    all_dates = sorted(set(fii_by_date.keys()) | set(dii_by_date.keys()), reverse=True)

    results = []
    for td in all_dates[:days]:
        fii = fii_by_date.get(td)
        dii = dii_by_date.get(td)
        results.append(FiiDiiResponse(
            trade_date=td,
            fii_net=fii.net_value_cr if fii else 0,
            dii_net=dii.net_value_cr if dii else 0,
            fii_buy=fii.buy_value_cr if fii else 0,
            fii_sell=fii.sell_value_cr if fii else 0,
            dii_buy=dii.buy_value_cr if dii else 0,
            dii_sell=dii.sell_value_cr if dii else 0,
        ))

    return results
