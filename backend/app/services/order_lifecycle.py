"""
Order Lifecycle State Machine.
Manages deterministic transitions for trade orders:
  OPEN → STOP_TRIGGERED → TAX_RECORDED
  OPEN → TARGET_REACHED → TAX_RECORDED
  OPEN → CLOSED (manual) → TAX_RECORDED
"""

from datetime import datetime
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import TradeOrder, Portfolio, Holding, User
from app.services.tax_engine import calculate_full_trade_pnl


# ─── Valid State Transitions ───────────────────────────────────────────────────

VALID_TRANSITIONS = {
    "OPEN": ["STOP_TRIGGERED", "TARGET_REACHED", "CLOSED"],
    "STOP_TRIGGERED": ["TAX_RECORDED"],
    "TARGET_REACHED": ["TAX_RECORDED"],
    "CLOSED": ["TAX_RECORDED"],
}


class OrderLifecycleError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


def validate_transition(current_status: str, new_status: str) -> bool:
    """Check if a state transition is valid."""
    allowed = VALID_TRANSITIONS.get(current_status, [])
    return new_status in allowed


# ─── Order Creation ────────────────────────────────────────────────────────────

def create_buy_order(
    db: Session,
    user_id: int,
    portfolio_id: int,
    symbol: str,
    quantity: int,
    entry_price: float,
    stop_loss: Optional[float] = None,
    target_price: Optional[float] = None,
    notes: Optional[str] = None,
) -> TradeOrder:
    """Create a new BUY order and corresponding holding."""

    # Create the trade order
    order = TradeOrder(
        user_id=user_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        order_type="BUY",
        status="OPEN",
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        entry_date=datetime.utcnow(),
        notes=notes,
    )
    db.add(order)

    # Create or update holding
    existing_holding = (
        db.query(Holding)
        .filter(
            Holding.portfolio_id == portfolio_id,
            Holding.symbol == symbol,
            Holding.status == "ACTIVE",
        )
        .first()
    )

    if existing_holding:
        # Average up/down
        total_qty = existing_holding.quantity + quantity
        total_cost = (existing_holding.avg_buy_price * existing_holding.quantity) + (entry_price * quantity)
        existing_holding.avg_buy_price = round(total_cost / total_qty, 2)
        existing_holding.quantity = total_qty
        existing_holding.stop_loss_price = stop_loss
        existing_holding.target_price = target_price
    else:
        holding = Holding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            avg_buy_price=entry_price,
            buy_date=datetime.utcnow().date(),
            status="ACTIVE",
            current_price=entry_price,
            stop_loss_price=stop_loss,
            target_price=target_price,
        )
        db.add(holding)

    # Update portfolio deployed capital
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio:
        trade_value = entry_price * quantity
        portfolio.deployed_capital += trade_value
        portfolio.cash_available -= trade_value

    db.commit()
    db.refresh(order)
    return order


# ─── State Transitions ────────────────────────────────────────────────────────

def trigger_stop_loss(
    db: Session,
    order_id: int,
    exit_price: Optional[float] = None,
) -> TradeOrder:
    """Transition order to STOP_TRIGGERED state."""
    order = db.query(TradeOrder).filter(TradeOrder.id == order_id).first()
    if not order:
        raise OrderLifecycleError(f"Order {order_id} not found")

    if not validate_transition(order.status, "STOP_TRIGGERED"):
        raise OrderLifecycleError(
            f"Cannot transition from {order.status} to STOP_TRIGGERED"
        )

    order.status = "STOP_TRIGGERED"
    order.exit_price = exit_price or order.stop_loss
    order.exit_date = datetime.utcnow()
    order.realized_pnl = (order.exit_price - order.entry_price) * order.quantity

    _close_holding(db, order)
    db.commit()
    db.refresh(order)
    return order


def trigger_target_reached(
    db: Session,
    order_id: int,
    exit_price: Optional[float] = None,
) -> TradeOrder:
    """Transition order to TARGET_REACHED state."""
    order = db.query(TradeOrder).filter(TradeOrder.id == order_id).first()
    if not order:
        raise OrderLifecycleError(f"Order {order_id} not found")

    if not validate_transition(order.status, "TARGET_REACHED"):
        raise OrderLifecycleError(
            f"Cannot transition from {order.status} to TARGET_REACHED"
        )

    order.status = "TARGET_REACHED"
    order.exit_price = exit_price or order.target_price
    order.exit_date = datetime.utcnow()
    order.realized_pnl = (order.exit_price - order.entry_price) * order.quantity

    _close_holding(db, order)
    db.commit()
    db.refresh(order)
    return order


def close_order_manually(
    db: Session,
    order_id: int,
    exit_price: float,
    notes: Optional[str] = None,
) -> TradeOrder:
    """Manually close an open order."""
    order = db.query(TradeOrder).filter(TradeOrder.id == order_id).first()
    if not order:
        raise OrderLifecycleError(f"Order {order_id} not found")

    if not validate_transition(order.status, "CLOSED"):
        raise OrderLifecycleError(
            f"Cannot transition from {order.status} to CLOSED"
        )

    order.status = "CLOSED"
    order.exit_price = exit_price
    order.exit_date = datetime.utcnow()
    order.realized_pnl = (exit_price - order.entry_price) * order.quantity
    if notes:
        order.notes = (order.notes or "") + f" | {notes}"

    _close_holding(db, order)
    db.commit()
    db.refresh(order)
    return order


def record_tax(db: Session, order_id: int) -> TradeOrder:
    """
    Transition a closed/stopped/targeted order to TAX_RECORDED.
    Calculates all transaction costs and tax liability.
    """
    order = db.query(TradeOrder).filter(TradeOrder.id == order_id).first()
    if not order:
        raise OrderLifecycleError(f"Order {order_id} not found")

    if not validate_transition(order.status, "TAX_RECORDED"):
        raise OrderLifecycleError(
            f"Cannot transition from {order.status} to TAX_RECORDED"
        )

    if not order.exit_price or not order.exit_date:
        raise OrderLifecycleError("Order must have exit price and date for tax recording")

    # Calculate holding days
    entry_dt = order.entry_date
    exit_dt = order.exit_date
    holding_days = (exit_dt - entry_dt).days

    # Get cumulative LTCG exemption used this financial year
    user = db.query(User).filter(User.id == order.user_id).first()
    ltcg_used = _get_ltcg_exemption_used(db, order.user_id)

    # Full P&L calculation
    pnl = calculate_full_trade_pnl(
        buy_price=order.entry_price,
        sell_price=order.exit_price,
        quantity=order.quantity,
        holding_days=holding_days,
        ltcg_exemption_used=ltcg_used,
    )

    # Update order with all cost details
    order.stt_paid = pnl["stt"]
    order.gst_paid = pnl["gst"]
    order.sebi_fee = pnl["sebi_fee"]
    order.brokerage = pnl["brokerage"]
    order.stamp_duty = pnl["stamp_duty"]
    order.exchange_txn_charge = pnl["exchange_txn_charge"]
    order.tax_liability = pnl["tax_amount"]
    order.tax_type = pnl["tax_type"]
    order.net_return = pnl["net_pnl"]
    order.status = "TAX_RECORDED"

    db.commit()
    db.refresh(order)
    return order


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _close_holding(db: Session, order: TradeOrder) -> None:
    """Close the holding associated with an order and update portfolio."""
    holding = (
        db.query(Holding)
        .filter(
            Holding.portfolio_id == order.portfolio_id,
            Holding.symbol == order.symbol,
            Holding.status == "ACTIVE",
        )
        .first()
    )

    if holding:
        if holding.quantity <= order.quantity:
            holding.status = "CLOSED"
        else:
            holding.quantity -= order.quantity

    # Update portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.id == order.portfolio_id).first()
    if portfolio and order.exit_price:
        sale_value = order.exit_price * order.quantity
        buy_value = order.entry_price * order.quantity
        portfolio.deployed_capital -= buy_value
        portfolio.cash_available += sale_value


def _get_ltcg_exemption_used(db: Session, user_id: int) -> float:
    """Get the total LTCG exemption already used in the current FY."""
    # Simplified: sum all LTCG gains from TAX_RECORDED orders
    from sqlalchemy import func

    result = (
        db.query(func.sum(TradeOrder.realized_pnl))
        .filter(
            TradeOrder.user_id == user_id,
            TradeOrder.status == "TAX_RECORDED",
            TradeOrder.tax_type == "LTCG",
            TradeOrder.realized_pnl > 0,
        )
        .scalar()
    )
    return float(result or 0.0)
