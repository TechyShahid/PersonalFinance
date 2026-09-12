"""
Pydantic v2 schemas for request/response validation across all API endpoints.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── User Schemas ───────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: str
    total_capital: float = 2500000.0
    core_allocation_pct: float = 70.0
    satellite_allocation_pct: float = 30.0
    max_concurrent_swings: int = 6
    max_risk_per_trade_pct: float = 1.0


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Portfolio Schemas ──────────────────────────────────────────────────────────

class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    portfolio_type: str
    deployed_capital: float
    cash_available: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Holding Schemas ────────────────────────────────────────────────────────────

class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    exchange: str
    quantity: int
    avg_buy_price: float
    buy_date: date
    status: str
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    stop_loss_price: Optional[float] = None
    target_price: Optional[float] = None

    class Config:
        from_attributes = True


# ─── EOD Data Schemas ───────────────────────────────────────────────────────────

class EodDataResponse(BaseModel):
    symbol: str
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    total_traded_qty: int
    deliverable_qty: Optional[int] = None
    delivery_pct: Optional[float] = None
    turnover_cr: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    atr_14: Optional[float] = None

    class Config:
        from_attributes = True


# ─── Screening Schemas ──────────────────────────────────────────────────────────

class ScreeningCandidateResponse(BaseModel):
    id: int
    symbol: str
    scan_date: date
    composite_score: float
    setup_type: str
    delivery_pct: Optional[float] = None
    turnover_cr: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    rationale: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ─── Trade Order Schemas ────────────────────────────────────────────────────────

class TradeOrderCreate(BaseModel):
    symbol: str
    order_type: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int
    entry_price: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    portfolio_type: str = Field(default="SATELLITE", pattern="^(CORE|SATELLITE)$")
    notes: Optional[str] = None


class TradeOrderResponse(BaseModel):
    id: int
    user_id: int
    portfolio_id: int
    symbol: str
    order_type: str
    status: str
    quantity: int
    entry_price: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    exit_price: Optional[float] = None
    entry_date: datetime
    exit_date: Optional[datetime] = None
    realized_pnl: Optional[float] = None
    stt_paid: Optional[float] = None
    gst_paid: Optional[float] = None
    sebi_fee: Optional[float] = None
    brokerage: Optional[float] = None
    stamp_duty: Optional[float] = None
    exchange_txn_charge: Optional[float] = None
    tax_liability: Optional[float] = None
    tax_type: Optional[str] = None
    net_return: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Position Sizing Schemas ───────────────────────────────────────────────────

class PositionSizeRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss_price: float
    portfolio_capital: Optional[float] = None
    risk_pct: Optional[float] = None


class PositionSizeResponse(BaseModel):
    symbol: str
    entry_price: float
    stop_loss_price: float
    risk_per_share: float
    shares_to_buy: int
    total_investment: float
    risk_amount: float
    risk_pct_of_portfolio: float
    target_price_2r: float
    potential_profit: float
    estimated_costs: dict
    net_pnl_at_target: float


# ─── Tax Estimate Schemas ───────────────────────────────────────────────────────

class TaxEstimateRequest(BaseModel):
    buy_price: float
    sell_price: float
    quantity: int
    holding_days: int
    brokerage_per_order: float = 20.0


class TaxEstimateResponse(BaseModel):
    gross_pnl: float
    stt: float
    exchange_txn_charge: float
    sebi_fee: float
    gst: float
    stamp_duty: float
    brokerage: float
    total_transaction_costs: float
    tax_type: str
    taxable_gain: float
    tax_amount: float
    net_pnl: float
    effective_return_pct: float


# ─── Dashboard Schemas ──────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_capital: float
    core_deployed: float
    core_cash: float
    satellite_deployed: float
    satellite_cash: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    active_swing_trades: int
    max_concurrent_swings: int
    todays_pnl: float
    win_rate: float
    total_trades: int


class PerformancePoint(BaseModel):
    date: date
    portfolio_value: float
    nifty_50_value: float
    nifty_midcap_150_value: float


class PerformanceResponse(BaseModel):
    data: List[PerformancePoint]
    portfolio_return_pct: float
    nifty_50_return_pct: float
    nifty_midcap_return_pct: float


# ─── Journal Schemas ────────────────────────────────────────────────────────────

class JournalStatsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_amount: float
    avg_loss_amount: float
    avg_hold_days: float
    avg_r_multiple: float
    max_drawdown: float
    total_net_pnl: float
    total_tax_paid: float
    expectancy: float
    stcg_total: float
    ltcg_total: float
    ltcg_exemption_used: float
    ltcg_exemption_remaining: float


# ─── FII/DII Schemas ───────────────────────────────────────────────────────────

class FiiDiiResponse(BaseModel):
    trade_date: date
    fii_net: float
    dii_net: float
    fii_buy: float
    fii_sell: float
    dii_buy: float
    dii_sell: float

    class Config:
        from_attributes = True
