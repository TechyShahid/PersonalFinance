"""
Risk Management Engine.
Handles ATR-based position sizing, concurrent position limits,
and profit target / trailing stop calculations.
"""

import math
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models import User, Portfolio, TradeOrder, Holding


def calculate_position_size(
    portfolio_capital: float,
    entry_price: float,
    stop_loss_price: float,
    max_risk_pct: float = 1.0,
) -> Dict:
    """
    Calculate the number of shares to buy based on ATR / stop distance.
    Max 1% portfolio risk per trade.

    Formula: shares = (portfolio_capital × max_risk_pct) / (entry - stop_loss)
    """
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share <= 0:
        risk_per_share = entry_price * 0.04  # Fallback 4%

    risk_amount = portfolio_capital * (max_risk_pct / 100.0)
    shares = math.floor(risk_amount / risk_per_share)

    # Ensure at least 1 share if affordable
    if shares <= 0 and portfolio_capital >= entry_price:
        shares = 1

    total_investment = shares * entry_price
    actual_risk = shares * risk_per_share
    risk_pct = (actual_risk / portfolio_capital * 100) if portfolio_capital > 0 else 0

    # 2R target
    target_price = entry_price + 2 * risk_per_share
    potential_profit = shares * 2 * risk_per_share

    return {
        "shares_to_buy": shares,
        "total_investment": round(total_investment, 2),
        "risk_amount": round(actual_risk, 2),
        "risk_pct_of_portfolio": round(risk_pct, 2),
        "risk_per_share": round(risk_per_share, 2),
        "target_price_2r": round(target_price, 2),
        "potential_profit": round(potential_profit, 2),
    }


def check_concurrent_positions(db: Session, user_id: int) -> Dict:
    """
    Check how many active swing trades the user has vs the limit.
    Returns current count and whether a new trade is allowed.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"active_trades": 0, "max_allowed": 6, "can_open_new": True}

    active_count = (
        db.query(TradeOrder)
        .filter(
            TradeOrder.user_id == user_id,
            TradeOrder.status == "OPEN",
            TradeOrder.order_type == "BUY",
        )
        .count()
    )

    return {
        "active_trades": active_count,
        "max_allowed": user.max_concurrent_swings,
        "can_open_new": active_count < user.max_concurrent_swings,
    }


def calculate_alert_levels(
    entry_price: float,
    stop_loss: float,
    risk_per_share: Optional[float] = None,
) -> Dict:
    """
    Calculate alert levels for a position:
    - 1R profit (breakeven move stop to entry)
    - 2R profit (primary target, +8% to +10%)
    - 3R profit (runner target)
    - Trailing stop levels
    """
    if risk_per_share is None:
        risk_per_share = abs(entry_price - stop_loss)

    return {
        "entry": round(entry_price, 2),
        "initial_stop": round(stop_loss, 2),
        "breakeven_level": round(entry_price, 2),  # Move stop to entry at 1R
        "target_1r": round(entry_price + risk_per_share, 2),
        "target_2r": round(entry_price + 2 * risk_per_share, 2),
        "target_3r": round(entry_price + 3 * risk_per_share, 2),
        "trail_stop_at_1r": round(entry_price, 2),
        "trail_stop_at_2r": round(entry_price + risk_per_share, 2),
        "trail_stop_at_3r": round(entry_price + 2 * risk_per_share, 2),
        "profit_pct_at_2r": round((2 * risk_per_share / entry_price) * 100, 2),
    }


def get_portfolio_risk_summary(db: Session, user_id: int) -> Dict:
    """
    Comprehensive risk summary for a user's portfolio.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

    satellite = next((p for p in portfolios if p.portfolio_type == "SATELLITE"), None)
    core = next((p for p in portfolios if p.portfolio_type == "CORE"), None)

    active_orders = (
        db.query(TradeOrder)
        .filter(TradeOrder.user_id == user_id, TradeOrder.status == "OPEN")
        .all()
    )

    total_at_risk = 0.0
    positions = []
    for order in active_orders:
        if order.stop_loss and order.entry_price:
            risk = (order.entry_price - order.stop_loss) * order.quantity
            total_at_risk += risk
            positions.append({
                "symbol": order.symbol,
                "risk_amount": round(risk, 2),
                "risk_pct": round(risk / user.total_capital * 100, 2) if user.total_capital > 0 else 0,
            })

    return {
        "total_capital": user.total_capital,
        "core_capital": core.deployed_capital + core.cash_available if core else 0,
        "satellite_capital": satellite.deployed_capital + satellite.cash_available if satellite else 0,
        "satellite_deployed": satellite.deployed_capital if satellite else 0,
        "satellite_cash": satellite.cash_available if satellite else 0,
        "active_positions": len(active_orders),
        "max_positions": user.max_concurrent_swings,
        "total_at_risk": round(total_at_risk, 2),
        "total_risk_pct": round(total_at_risk / user.total_capital * 100, 2) if user.total_capital > 0 else 0,
        "position_risks": positions,
    }
