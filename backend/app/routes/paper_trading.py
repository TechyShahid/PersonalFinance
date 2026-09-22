"""
Paper Trading API Routes.
Simulated trading engine for Indian equities (NSE/BSE) with virtual capital,
live market quotes, realistic Indian equity transaction charges, positions tracking,
trade journaling, and 1-click square off.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.database import get_db
from app.models import PaperAccount, PaperPosition, PaperOrder, Stock, DailyEodData, User
from app.schemas import (
    PaperAccountResponse,
    PaperPositionResponse,
    PaperOrderCreate,
    PaperOrderResponse,
    PaperQuoteResponse,
)
from app.services.candle_service import get_stock_candles

router = APIRouter(prefix="/api/paper-trading", tags=["Paper Trading"])


# ─── Indian Equity Transaction Charges Calculation ───────────────────────────

def calculate_charges(order_side: str, price: float, quantity: int) -> float:
    """
    Calculate realistic Indian equity delivery transaction charges:
    - Brokerage: ₹20 flat
    - STT (Securities Transaction Tax): 0.1% on turnover
    - Exchange Transaction Charge: 0.00345% on turnover
    - SEBI Turnover Charge: 0.0001% on turnover
    - Stamp Duty: 0.015% on buy turnover only
    - GST: 18% on (Brokerage + Exchange Txn + SEBI)
    """
    turnover = price * quantity
    brokerage = 20.0
    stt = turnover * 0.001
    exchange_charge = turnover * 0.0000345
    sebi_fee = turnover * 0.000001
    stamp_duty = turnover * 0.00015 if order_side == "BUY" else 0.0
    gst = (brokerage + exchange_charge + sebi_fee) * 0.18

    total_charges = brokerage + stt + exchange_charge + sebi_fee + stamp_duty + gst
    return round(total_charges, 2)


# ─── Helper: Get or Create Default Account ────────────────────────────────────

def get_or_create_paper_account(db: Session) -> PaperAccount:
    """Retrieve the primary paper trading account or create one with ₹10,00,000 initial capital."""
    account = db.query(PaperAccount).first()
    if not account:
        user = db.query(User).first()
        account = PaperAccount(
            user_id=user.id if user else None,
            name="Virtual Trading Account",
            initial_capital=1000000.0,
            cash_balance=1000000.0,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


# ─── Helper: Fetch Quote ──────────────────────────────────────────────────────

def get_latest_quote(symbol: str, exchange: str = "NSE", db: Optional[Session] = None) -> dict:
    """Fetch live or cached market quote for a symbol."""
    clean_sym = symbol.strip().upper()
    company_name = clean_sym

    if db:
        stock = db.query(Stock).filter(
            or_(
                Stock.nse_symbol == clean_sym,
                Stock.bse_symbol == clean_sym,
            )
        ).first()
        if stock:
            company_name = stock.company_name

    try:
        candle_data = get_stock_candles(clean_sym, exchange=exchange, period="5d", interval="1d")
        summary = candle_data.get("summary", {})
        curr_price = float(summary.get("current_price", 0.0))
        if curr_price > 0:
            return {
                "symbol": clean_sym,
                "company_name": company_name,
                "exchange": exchange,
                "current_price": round(curr_price, 2),
                "previous_close": round(float(summary.get("previous_close", curr_price)), 2),
                "change_pct": round(float(summary.get("change_pct", 0.0)), 2),
                "high_period": round(float(summary.get("high_period", curr_price)), 2),
                "low_period": round(float(summary.get("low_period", curr_price)), 2),
                "volume": int(summary.get("latest_volume", 0)),
            }
    except Exception as e:
        print(f"Candle fetch failed for {clean_sym}: {e}")

    # Fallback to EOD database if candle fetch encounters error
    if db:
        eod = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == clean_sym)
            .order_by(DailyEodData.trade_date.desc())
            .first()
        )
        if eod:
            prev = eod.prev_close or eod.close_price
            chg = ((eod.close_price - prev) / prev * 100) if prev else 0.0
            return {
                "symbol": clean_sym,
                "company_name": company_name,
                "exchange": exchange,
                "current_price": round(float(eod.close_price), 2),
                "previous_close": round(float(prev), 2),
                "change_pct": round(float(chg), 2),
                "high_period": round(float(eod.high_price), 2),
                "low_period": round(float(eod.low_price), 2),
                "volume": int(eod.total_traded_qty),
            }

    # Ultimate fallback
    return {
        "symbol": clean_sym,
        "company_name": company_name,
        "exchange": exchange,
        "current_price": 500.0,
        "previous_close": 500.0,
        "change_pct": 0.0,
        "high_period": 500.0,
        "low_period": 500.0,
        "volume": 10000,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/quote/{symbol}", response_model=PaperQuoteResponse)
def get_quote(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: Session = Depends(get_db),
):
    """Get live or cached market quote for a stock."""
    quote = get_latest_quote(symbol, exchange=exchange, db=db)
    return PaperQuoteResponse(**quote)


@router.get("/account", response_model=PaperAccountResponse)
def get_account_summary(db: Session = Depends(get_db)):
    """Get paper trading account summary, total portfolio value, and performance metrics."""
    account = get_or_create_paper_account(db)
    positions = db.query(PaperPosition).filter(PaperPosition.account_id == account.id).all()
    orders = db.query(PaperOrder).filter(PaperOrder.account_id == account.id).all()

    invested_capital = 0.0
    current_portfolio_value = 0.0

    # Calculate positions values
    for pos in positions:
        quote = get_latest_quote(pos.symbol, exchange=pos.exchange, db=db)
        curr_p = quote["current_price"]
        pos.current_price = curr_p

        pos_invested = pos.avg_price * pos.quantity
        pos_current = curr_p * pos.quantity

        invested_capital += pos_invested
        current_portfolio_value += pos_current

    db.commit()

    total_portfolio_value = round(account.cash_balance + current_portfolio_value, 2)
    unrealized_pnl = round(current_portfolio_value - invested_capital, 2)
    unrealized_pnl_pct = (
        round((unrealized_pnl / invested_capital) * 100, 2) if invested_capital > 0 else 0.0
    )

    # Realized P&L and metrics from closed/sell orders
    sell_orders = [o for o in orders if o.order_side == "SELL" and o.status == "EXECUTED"]
    realized_pnl = round(sum(o.realized_pnl or 0.0 for o in sell_orders), 2)
    total_charges_paid = round(sum(o.charges or 0.0 for o in orders if o.status == "EXECUTED"), 2)

    net_pnl = round(total_portfolio_value - account.initial_capital, 2)
    net_return_pct = round((net_pnl / account.initial_capital) * 100, 2)

    winning_trades = len([o for o in sell_orders if (o.realized_pnl or 0.0) > 0])
    losing_trades = len([o for o in sell_orders if (o.realized_pnl or 0.0) <= 0])
    total_closed = len(sell_orders)
    win_rate_pct = round((winning_trades / total_closed * 100), 1) if total_closed > 0 else 0.0

    return PaperAccountResponse(
        id=account.id,
        name=account.name,
        initial_capital=account.initial_capital,
        cash_balance=round(account.cash_balance, 2),
        invested_capital=round(invested_capital, 2),
        total_portfolio_value=total_portfolio_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        realized_pnl=realized_pnl,
        total_charges_paid=total_charges_paid,
        net_pnl=net_pnl,
        net_return_pct=net_return_pct,
        open_positions_count=len(positions),
        total_trades_count=len(orders),
        winning_trades_count=winning_trades,
        losing_trades_count=losing_trades,
        win_rate_pct=win_rate_pct,
        created_at=account.created_at,
    )


@router.get("/positions", response_model=List[PaperPositionResponse])
def get_positions(db: Session = Depends(get_db)):
    """Get all open paper trading positions with live unrealized P&L."""
    account = get_or_create_paper_account(db)
    positions = (
        db.query(PaperPosition)
        .filter(PaperPosition.account_id == account.id)
        .order_by(PaperPosition.created_at.desc())
        .all()
    )

    results = []
    for pos in positions:
        quote = get_latest_quote(pos.symbol, exchange=pos.exchange, db=db)
        curr_p = quote["current_price"]
        pos.current_price = curr_p

        invested = round(pos.avg_price * pos.quantity, 2)
        curr_val = round(curr_p * pos.quantity, 2)
        pnl = round(curr_val - invested, 2)
        pnl_pct = round((pnl / invested) * 100, 2) if invested > 0 else 0.0

        results.append(
            PaperPositionResponse(
                id=pos.id,
                account_id=pos.account_id,
                symbol=pos.symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=round(pos.avg_price, 2),
                current_price=round(curr_p, 2),
                invested_value=invested,
                current_value=curr_val,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                stop_loss=pos.stop_loss,
                target_price=pos.target_price,
                notes=pos.notes,
                created_at=pos.created_at,
                updated_at=pos.updated_at,
            )
        )

    db.commit()
    return results


@router.get("/orders", response_model=List[PaperOrderResponse])
def get_orders(db: Session = Depends(get_db)):
    """Get full history of paper orders/trades."""
    account = get_or_create_paper_account(db)
    orders = (
        db.query(PaperOrder)
        .filter(PaperOrder.account_id == account.id)
        .order_by(PaperOrder.created_at.desc())
        .all()
    )
    return orders


@router.post("/order", response_model=PaperOrderResponse)
def place_order(order_data: PaperOrderCreate, db: Session = Depends(get_db)):
    """
    Execute a paper trade order (BUY or SELL).
    Validates capital, updates cash balance, manages positions, and logs transaction charges.
    """
    account = get_or_create_paper_account(db)
    clean_sym = order_data.symbol.strip().upper()

    # Determine execution price
    exec_price = order_data.price
    if not exec_price or exec_price <= 0:
        quote = get_latest_quote(clean_sym, exchange=order_data.exchange, db=db)
        exec_price = quote["current_price"]

    exec_price = round(float(exec_price), 2)
    quantity = order_data.quantity
    order_side = order_data.order_side.upper()
    charges = calculate_charges(order_side, exec_price, quantity)

    if order_side == "BUY":
        total_required = round((exec_price * quantity) + charges, 2)
        if total_required > account.cash_balance:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient funds. Required: ₹{total_required:,.2f} "
                    f"(including ₹{charges:,.2f} charges), Available: ₹{account.cash_balance:,.2f}"
                ),
            )

        # Deduct cash
        account.cash_balance = round(account.cash_balance - total_required, 2)

        # Update or create position
        pos = (
            db.query(PaperPosition)
            .filter(
                PaperPosition.account_id == account.id,
                PaperPosition.symbol == clean_sym,
            )
            .first()
        )

        if pos:
            # Weighted average price
            total_qty = pos.quantity + quantity
            total_cost = (pos.avg_price * pos.quantity) + (exec_price * quantity)
            pos.avg_price = round(total_cost / total_qty, 2)
            pos.quantity = total_qty
            pos.current_price = exec_price
            if order_data.stop_loss:
                pos.stop_loss = order_data.stop_loss
            if order_data.target_price:
                pos.target_price = order_data.target_price
            if order_data.notes:
                pos.notes = (pos.notes or "") + f" | {order_data.notes}"
        else:
            pos = PaperPosition(
                account_id=account.id,
                symbol=clean_sym,
                exchange=order_data.exchange,
                quantity=quantity,
                avg_price=exec_price,
                current_price=exec_price,
                stop_loss=order_data.stop_loss,
                target_price=order_data.target_price,
                notes=order_data.notes,
            )
            db.add(pos)

        # Record executed order
        order = PaperOrder(
            account_id=account.id,
            symbol=clean_sym,
            exchange=order_data.exchange,
            order_side="BUY",
            order_type=order_data.order_type,
            quantity=quantity,
            price=exec_price,
            stop_loss=order_data.stop_loss,
            target_price=order_data.target_price,
            realized_pnl=0.0,
            pnl_pct=0.0,
            charges=charges,
            status="EXECUTED",
            notes=order_data.notes,
            created_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    elif order_side == "SELL":
        # Find existing position
        pos = (
            db.query(PaperPosition)
            .filter(
                PaperPosition.account_id == account.id,
                PaperPosition.symbol == clean_sym,
            )
            .first()
        )

        if not pos or pos.quantity < quantity:
            current_held = pos.quantity if pos else 0
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sell {quantity} shares of {clean_sym}. Currently holding {current_held} shares.",
            )

        # Calculate realized P&L
        gross_pnl = (exec_price - pos.avg_price) * quantity
        net_realized_pnl = round(gross_pnl - charges, 2)
        pnl_pct = round(((exec_price - pos.avg_price) / pos.avg_price) * 100, 2) if pos.avg_price > 0 else 0.0

        # Credit proceeds to cash balance (turnover minus charges)
        net_proceeds = round((exec_price * quantity) - charges, 2)
        account.cash_balance = round(account.cash_balance + net_proceeds, 2)

        # Update or remove position
        if pos.quantity == quantity:
            db.delete(pos)
        else:
            pos.quantity -= quantity
            pos.current_price = exec_price

        # Record executed order
        order = PaperOrder(
            account_id=account.id,
            symbol=clean_sym,
            exchange=order_data.exchange,
            order_side="SELL",
            order_type=order_data.order_type,
            quantity=quantity,
            price=exec_price,
            stop_loss=pos.stop_loss if pos else None,
            target_price=pos.target_price if pos else None,
            realized_pnl=net_realized_pnl,
            pnl_pct=pnl_pct,
            charges=charges,
            status="EXECUTED",
            notes=order_data.notes,
            created_at=datetime.utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    else:
        raise HTTPException(status_code=400, detail="Invalid order side")


@router.post("/close-position/{position_id}", response_model=PaperOrderResponse)
def close_position(position_id: int, db: Session = Depends(get_db)):
    """Square off / exit an entire position at the current market price in 1-click."""
    account = get_or_create_paper_account(db)
    pos = (
        db.query(PaperPosition)
        .filter(
            PaperPosition.id == position_id,
            PaperPosition.account_id == account.id,
        )
        .first()
    )

    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    quote = get_latest_quote(pos.symbol, exchange=pos.exchange, db=db)
    exit_price = quote["current_price"]

    sell_order = PaperOrderCreate(
        symbol=pos.symbol,
        exchange=pos.exchange,
        order_side="SELL",
        order_type="MARKET",
        quantity=pos.quantity,
        price=exit_price,
        notes="Position squared off manually at market price",
    )

    return place_order(sell_order, db=db)


@router.post("/reset", response_model=PaperAccountResponse)
def reset_account(db: Session = Depends(get_db)):
    """Reset the paper trading account back to fresh ₹10,00,000 cash and clear all positions/orders."""
    account = get_or_create_paper_account(db)

    # Delete all positions and orders for this account
    db.query(PaperPosition).filter(PaperPosition.account_id == account.id).delete()
    db.query(PaperOrder).filter(PaperOrder.account_id == account.id).delete()

    account.initial_capital = 1000000.0
    account.cash_balance = 1000000.0
    account.updated_at = datetime.utcnow()

    db.commit()
    return get_account_summary(db=db)
