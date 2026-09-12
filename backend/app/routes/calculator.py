"""
Position Sizing & Tax Estimation Calculator API Routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import (
    PositionSizeRequest, PositionSizeResponse,
    TaxEstimateRequest, TaxEstimateResponse,
)
from app.services.risk_engine import calculate_position_size
from app.services.tax_engine import (
    calculate_full_trade_pnl,
    estimate_position_costs,
    calculate_transaction_costs,
)

router = APIRouter(prefix="/api/calculator", tags=["Calculator"])


@router.post("/position-size", response_model=PositionSizeResponse)
def compute_position_size(req: PositionSizeRequest, db: Session = Depends(get_db)):
    """Calculate exact position size based on risk parameters."""
    user = db.query(User).first()

    # Use provided capital or user's satellite capital
    portfolio_capital = req.portfolio_capital
    risk_pct = req.risk_pct

    if not portfolio_capital and user:
        portfolio_capital = user.total_capital * (user.satellite_allocation_pct / 100)
    elif not portfolio_capital:
        portfolio_capital = 750000.0  # Default ₹7.5L satellite

    if not risk_pct and user:
        risk_pct = user.max_risk_per_trade_pct
    elif not risk_pct:
        risk_pct = 1.0

    sizing = calculate_position_size(
        portfolio_capital=portfolio_capital,
        entry_price=req.entry_price,
        stop_loss_price=req.stop_loss_price,
        max_risk_pct=risk_pct,
    )

    # Estimate costs at target
    costs = estimate_position_costs(
        entry_price=req.entry_price,
        target_price=sizing["target_price_2r"],
        stop_loss_price=req.stop_loss_price,
        quantity=sizing["shares_to_buy"],
    )

    return PositionSizeResponse(
        symbol=req.symbol.upper(),
        entry_price=req.entry_price,
        stop_loss_price=req.stop_loss_price,
        risk_per_share=sizing["risk_per_share"],
        shares_to_buy=sizing["shares_to_buy"],
        total_investment=sizing["total_investment"],
        risk_amount=sizing["risk_amount"],
        risk_pct_of_portfolio=sizing["risk_pct_of_portfolio"],
        target_price_2r=sizing["target_price_2r"],
        potential_profit=sizing["potential_profit"],
        estimated_costs=costs,
        net_pnl_at_target=costs["at_target"]["net_pnl"],
    )


@router.post("/tax-estimate", response_model=TaxEstimateResponse)
def estimate_tax(req: TaxEstimateRequest, db: Session = Depends(get_db)):
    """Estimate tax and costs for a hypothetical trade."""
    result = calculate_full_trade_pnl(
        buy_price=req.buy_price,
        sell_price=req.sell_price,
        quantity=req.quantity,
        holding_days=req.holding_days,
        brokerage_per_order=req.brokerage_per_order,
    )

    buy_value = req.buy_price * req.quantity
    sell_value = req.sell_price * req.quantity

    return TaxEstimateResponse(
        gross_pnl=result["gross_pnl"],
        stt=result["stt"],
        exchange_txn_charge=result["exchange_txn_charge"],
        sebi_fee=result["sebi_fee"],
        gst=result["gst"],
        stamp_duty=result["stamp_duty"],
        brokerage=result["brokerage"],
        total_transaction_costs=result["total_transaction_costs"],
        tax_type=result["tax_type"],
        taxable_gain=result["taxable_gain"],
        tax_amount=result["tax_amount"],
        net_pnl=result["net_pnl"],
        effective_return_pct=result["effective_return_pct"],
    )
