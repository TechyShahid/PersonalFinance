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
    cap_category: Optional[str] = "MIDCAP"
    market_cap_cr: Optional[float] = None
    sector: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class MidSmallSwingCandidateResponse(BaseModel):
    symbol: str
    company_name: str
    market_cap_tier: str  # MIDCAP | SMALLCAP
    market_cap_cr: float
    sector: str
    setup_type: str       # VCP | PULLBACK | BREAKOUT | ACCUMULATION
    composite_score: float
    delivery_multiple: float
    delivery_pct: float
    deliverable_value_cr: float
    turnover_cr: float
    adv_20d: int
    relative_strength_score: float
    rs_benchmark: str
    pivot_price: float
    entry_price: float
    suggested_stop_loss: float
    target_price: float
    risk_reward_ratio: float
    asm_gsm_stage: int = 0
    rationale: str


class PennySwingCandidateResponse(BaseModel):
    symbol: str
    company_name: str
    exchange: str                  # NSE | BSE
    market_cap_cr: float
    sector: str
    price_band_pct: float          # 10.0 or 20.0
    circuit_status: str            # NORMAL_TRADING
    setup_type: str                # QUIET_BASE_ACCUMULATION | HIGHER_LOW_REVERSAL | ACCUMULATION_PULSE
    composite_score: float
    operator_risk_score: float     # 0 - 100
    risk_classification: str       # LOW_RISK | MODERATE | ELEVATED
    entry_price: float
    suggested_stop_loss: float
    target_price: float
    risk_reward_ratio: float
    volume_surge_multiple: float
    delivery_pct: float
    deliverable_value_cr: float
    turnover_cr: float
    trade_count: int
    bid_ask_spread_pct: float
    max_safe_shares: int
    max_safe_capital: float
    capital_pct: float
    circuit_warning: str
    rationale: str


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


# ─── Stock Universe Schemas ───────────────────────────────────────────────────

class StockBase(BaseModel):
    sr_no: int
    company_name: str
    isin: str
    bse_symbol: Optional[str] = None
    bse_mcap_cr: Optional[float] = None
    nse_symbol: Optional[str] = None
    nse_mcap_cr: Optional[float] = None
    msei_symbol: Optional[str] = None
    msei_mcap_cr: Optional[float] = None
    avg_mcap_cr: Optional[float] = None
    category: Optional[str] = None


class StockResponse(StockBase):
    id: int

    class Config:
        from_attributes = True


# ─── Newly Listed Stocks (IPO Tracker) Schemas ────────────────────────────────

class NewlyListedStockResponse(BaseModel):
    id: int
    symbol: str
    company_name: str
    series: str = "EQ"
    listing_date: date
    days_since_listing: int
    category: Optional[str] = None
    market_cap_cr: Optional[float] = None
    listing_price: Optional[float] = None
    current_price: Optional[float] = None
    change_pct: Optional[float] = 0.0
    return_since_listing_pct: Optional[float] = 0.0
    all_time_high: Optional[float] = None
    drawdown_from_high_pct: Optional[float] = 0.0
    volume: Optional[int] = 0
    turnover_cr: Optional[float] = 0.0
    delivery_pct: Optional[float] = 0.0
    performance_rank: Optional[int] = None
    is_outperformer: bool = False
    is_relisted: bool = False
    listing_type: Optional[str] = "FRESH_IPO"  # FRESH_IPO | RE_LISTED
    performance_tier: Optional[str] = None  # MULTIBAGGER | HIGH_FLYER | OUTPERFORMER | NEUTRAL | LAGGARD
    operating_profit_cr: Optional[float] = None
    prev_operating_profit_cr: Optional[float] = None
    operating_profit_growth_pct: Optional[float] = None
    is_op_profit_growing: bool = False

    class Config:
        from_attributes = True


class NewListingsStatsResponse(BaseModel):
    total_listings: int
    fresh_ipos_count: int = 0
    relisted_count: int = 0
    outperformers_count: int
    outperformers_pct: float
    median_return_pct: float
    average_return_pct: float
    op_profit_growing_count: int = 0
    op_profit_growing_pct: float = 0.0
    top_performer: Optional[dict] = None
    category_breakdown: dict


# ─── Paper Trading Schemas ───────────────────────────────────────────────────────

class PaperPositionResponse(BaseModel):
    id: int
    account_id: int
    symbol: str
    exchange: str
    quantity: int
    avg_price: float
    current_price: Optional[float] = None
    invested_value: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperOrderCreate(BaseModel):
    symbol: str
    exchange: str = Field(default="NSE", pattern="^(NSE|BSE)$")
    order_side: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    quantity: int = Field(..., gt=0)
    price: Optional[float] = None  # If not provided, fetched from current market price
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None


class PaperOrderResponse(BaseModel):
    id: int
    account_id: int
    symbol: str
    exchange: str
    order_side: str
    order_type: str
    quantity: int
    price: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    realized_pnl: Optional[float] = 0.0
    pnl_pct: Optional[float] = 0.0
    charges: Optional[float] = 0.0
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaperAccountResponse(BaseModel):
    id: int
    name: str
    initial_capital: float
    cash_balance: float
    invested_capital: float
    total_portfolio_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    total_charges_paid: float
    net_pnl: float
    net_return_pct: float
    open_positions_count: int
    total_trades_count: int
    winning_trades_count: int
    losing_trades_count: int
    win_rate_pct: float
    created_at: datetime

    class Config:
        from_attributes = True


class PaperQuoteResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    current_price: float
    previous_close: Optional[float] = None
    change_pct: Optional[float] = 0.0
    high_period: Optional[float] = None
    low_period: Optional[float] = None
    volume: Optional[int] = 0




