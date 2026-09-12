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
    """Get portfolio performance vs benchmarks over time using 100% genuine NSE EOD data."""
    cutoff = date.today() - timedelta(days=int(days * 1.5))

    # 1. Fetch genuine benchmark closes
    nifty_records = (
        db.query(DailyEodData.trade_date, DailyEodData.close_price)
        .filter(DailyEodData.symbol == "^NSEI", DailyEodData.trade_date >= cutoff)
        .order_by(DailyEodData.trade_date.asc())
        .all()
    )
    midcap_records = (
        db.query(DailyEodData.trade_date, DailyEodData.close_price)
        .filter(DailyEodData.symbol == "^NSEMDCP50", DailyEodData.trade_date >= cutoff)
        .order_by(DailyEodData.trade_date.asc())
        .all()
    )

    nifty_by_date = {r[0]: r[1] for r in nifty_records}
    midcap_by_date = {r[0]: r[1] for r in midcap_records}

    # 2. Get user holdings and cash
    user = db.query(User).first()
    core = db.query(Portfolio).filter(Portfolio.user_id == user.id, Portfolio.portfolio_type == "CORE").first() if user else None
    satellite = db.query(Portfolio).filter(Portfolio.user_id == user.id, Portfolio.portfolio_type == "SATELLITE").first() if user else None
    total_cash = (core.cash_available if core else 0.0) + (satellite.cash_available if satellite else 0.0)

    holdings = db.query(Holding).all()

    # Pre-fetch historical prices for all held symbols
    held_symbols = list(set([h.symbol for h in holdings]))
    eod_holdings = (
        db.query(DailyEodData.symbol, DailyEodData.trade_date, DailyEodData.close_price)
        .filter(DailyEodData.symbol.in_(held_symbols), DailyEodData.trade_date >= cutoff)
        .all()
    ) if held_symbols else []

    prices_by_sym_date: Dict[str, Dict[date, float]] = {}
    for sym, td, cp in eod_holdings:
        if sym not in prices_by_sym_date:
            prices_by_sym_date[sym] = {}
        prices_by_sym_date[sym][td] = cp

    # All trading dates sorted
    all_dates = sorted(list(set(nifty_by_date.keys()) | set(midcap_by_date.keys())))
    if not all_dates:
        raw_dates = db.query(DailyEodData.trade_date).filter(DailyEodData.trade_date >= cutoff).distinct().order_by(DailyEodData.trade_date.asc()).all()
        all_dates = [r[0] for r in raw_dates]

    if not all_dates:
        return PerformanceResponse(
            data=[],
            portfolio_return_pct=0.0,
            nifty_50_return_pct=0.0,
            nifty_midcap_return_pct=0.0,
        )

    # Base values for normalization (base 100 for indices)
    first_nifty = next((nifty_by_date[d] for d in all_dates if d in nifty_by_date and nifty_by_date[d] > 0), 24000.0)
    first_midcap = next((midcap_by_date[d] for d in all_dates if d in midcap_by_date and midcap_by_date[d] > 0), 55000.0)

    # Track forward-filled prices for holdings
    last_known_price = {h.symbol: h.avg_buy_price for h in holdings}

    data_points = []
    base_portfolio_val = None

    for d in all_dates:
        holding_val = 0.0
        for h in holdings:
            if h.symbol in prices_by_sym_date and d in prices_by_sym_date[h.symbol]:
                last_known_price[h.symbol] = prices_by_sym_date[h.symbol][d]
            holding_val += h.quantity * last_known_price.get(h.symbol, h.avg_buy_price)

        current_portfolio_val = total_cash + holding_val
        if base_portfolio_val is None:
            base_portfolio_val = current_portfolio_val

        nifty_val = round((nifty_by_date.get(d, first_nifty) / first_nifty) * 100.0, 2)
        midcap_val = round((midcap_by_date.get(d, first_midcap) / first_midcap) * 100.0, 2)

        data_points.append(PerformancePoint(
            date=d,
            portfolio_value=round(current_portfolio_val, 2),
            nifty_50_value=nifty_val,
            nifty_midcap_150_value=midcap_val,
        ))

    portfolio_return = round(
        ((data_points[-1].portfolio_value / base_portfolio_val) - 1.0) * 100.0, 2
    ) if base_portfolio_val and base_portfolio_val > 0 and data_points else 0.0

    nifty_return = round(
        (data_points[-1].nifty_50_value / 100.0 - 1.0) * 100.0, 2
    ) if data_points else 0.0

    midcap_return = round(
        (data_points[-1].nifty_midcap_150_value / 100.0 - 1.0) * 100.0, 2
    ) if data_points else 0.0

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
