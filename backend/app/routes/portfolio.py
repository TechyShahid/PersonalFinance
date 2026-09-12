"""
Portfolio API Routes.
Holdings management, trade execution, and portfolio details.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Portfolio, Holding, TradeOrder
from app.schemas import (
    PortfolioResponse, HoldingResponse, TradeOrderCreate,
    TradeOrderResponse,
)
from app.services.risk_engine import check_concurrent_positions, calculate_position_size
from app.services.order_lifecycle import create_buy_order, close_order_manually, record_tax

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("/", response_model=List[PortfolioResponse])
def get_portfolios(db: Session = Depends(get_db)):
    """Get all portfolios for the demo user."""
    user = db.query(User).first()
    if not user:
        return []
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    return portfolios


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    """Get portfolio details."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/holdings/all", response_model=List[HoldingResponse])
def get_all_holdings(
    portfolio_type: Optional[str] = None,
    status: str = "ACTIVE",
    db: Session = Depends(get_db),
):
    """Get all holdings, optionally filtered by portfolio type."""
    user = db.query(User).first()
    if not user:
        return []

    query = db.query(Holding).join(Portfolio).filter(Portfolio.user_id == user.id)

    if portfolio_type:
        query = query.filter(Portfolio.portfolio_type == portfolio_type.upper())
    if status:
        query = query.filter(Holding.status == status.upper())

    return query.all()


@router.post("/trade", response_model=TradeOrderResponse)
def execute_trade(trade: TradeOrderCreate, db: Session = Depends(get_db)):
    """Execute a new trade (buy/sell)."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found")

    # Find the appropriate portfolio
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.user_id == user.id,
            Portfolio.portfolio_type == trade.portfolio_type,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"{trade.portfolio_type} portfolio not found")

    if trade.order_type == "BUY":
        # Check concurrent position limit
        pos_check = check_concurrent_positions(db, user.id)
        if not pos_check["can_open_new"]:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum concurrent swing trades ({pos_check['max_allowed']}) reached",
            )

        # Check sufficient cash
        total_cost = trade.entry_price * trade.quantity
        if total_cost > portfolio.cash_available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient cash. Available: ₹{portfolio.cash_available:,.2f}, Required: ₹{total_cost:,.2f}",
            )

        order = create_buy_order(
            db=db,
            user_id=user.id,
            portfolio_id=portfolio.id,
            symbol=trade.symbol.upper(),
            quantity=trade.quantity,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            target_price=trade.target_price,
            notes=trade.notes,
        )
        return order

    elif trade.order_type == "SELL":
        # Find the open order for this symbol
        open_order = (
            db.query(TradeOrder)
            .filter(
                TradeOrder.user_id == user.id,
                TradeOrder.symbol == trade.symbol.upper(),
                TradeOrder.status == "OPEN",
            )
            .first()
        )
        if not open_order:
            raise HTTPException(status_code=404, detail=f"No open position found for {trade.symbol}")

        closed = close_order_manually(db, open_order.id, trade.entry_price, trade.notes)
        recorded = record_tax(db, closed.id)
        return recorded


@router.get("/orders/active", response_model=List[TradeOrderResponse])
def get_active_orders(db: Session = Depends(get_db)):
    """Get all active (OPEN) orders."""
    user = db.query(User).first()
    if not user:
        return []
    return (
        db.query(TradeOrder)
        .filter(TradeOrder.user_id == user.id, TradeOrder.status == "OPEN")
        .order_by(TradeOrder.entry_date.desc())
        .all()
    )
