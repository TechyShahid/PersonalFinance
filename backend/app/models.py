"""
SQLAlchemy ORM Models for the Personal Finance & Swing Trading Platform.
Covers users, portfolios, holdings, EOD market data, screening results,
trade orders, and FII/DII participant data.
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, Date, DateTime,
    Boolean, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    total_capital = Column(Float, nullable=False, default=0.0)
    core_allocation_pct = Column(Float, nullable=False, default=70.0)
    satellite_allocation_pct = Column(Float, nullable=False, default=30.0)
    max_concurrent_swings = Column(Integer, nullable=False, default=6)
    max_risk_per_trade_pct = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    trade_orders = relationship("TradeOrder", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_type = Column(String(20), nullable=False)  # CORE | SATELLITE
    deployed_capital = Column(Float, nullable=False, default=0.0)
    cash_available = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    trade_orders = relationship("TradeOrder", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(5), nullable=False, default="NSE")
    quantity = Column(Integer, nullable=False)
    avg_buy_price = Column(Float, nullable=False)
    buy_date = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default="ACTIVE")  # ACTIVE | CLOSED
    current_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True, default=0.0)
    stop_loss_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class DailyEodData(Base):
    __tablename__ = "daily_eod_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    series = Column(String(5), nullable=False, default="EQ")
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    last_price = Column(Float, nullable=True)
    prev_close = Column(Float, nullable=True)
    total_traded_qty = Column(BigInteger, nullable=False, default=0)
    total_traded_value = Column(Float, nullable=False, default=0.0)
    deliverable_qty = Column(BigInteger, nullable=True, default=0)
    delivery_pct = Column(Float, nullable=True, default=0.0)
    turnover_cr = Column(Float, nullable=True, default=0.0)

    # Computed technicals (updated by ingestion pipeline)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    vcp_score = Column(Float, nullable=True, default=0.0)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uix_symbol_date"),
        Index("ix_eod_symbol_date", "symbol", "trade_date"),
    )


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    scan_date = Column(Date, nullable=False, index=True)
    composite_score = Column(Float, nullable=False, default=0.0)
    setup_type = Column(String(30), nullable=False)  # VCP | EMA_PULLBACK | ACCUMULATION
    delivery_pct = Column(Float, nullable=True)
    turnover_cr = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    rationale = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("symbol", "scan_date", name="uix_screen_symbol_date"),
    )


class TradeOrder(Base):
    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    order_type = Column(String(5), nullable=False)  # BUY | SELL
    status = Column(String(20), nullable=False, default="OPEN")
    # OPEN | STOP_TRIGGERED | TARGET_REACHED | CLOSED | TAX_RECORDED
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    entry_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    exit_date = Column(DateTime, nullable=True)
    realized_pnl = Column(Float, nullable=True, default=0.0)

    # Transaction costs
    stt_paid = Column(Float, nullable=True, default=0.0)
    gst_paid = Column(Float, nullable=True, default=0.0)
    sebi_fee = Column(Float, nullable=True, default=0.0)
    brokerage = Column(Float, nullable=True, default=0.0)
    stamp_duty = Column(Float, nullable=True, default=0.0)
    exchange_txn_charge = Column(Float, nullable=True, default=0.0)
    tax_liability = Column(Float, nullable=True, default=0.0)
    tax_type = Column(String(10), nullable=True)  # STCG | LTCG | EXEMPT
    net_return = Column(Float, nullable=True, default=0.0)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="trade_orders")
    portfolio = relationship("Portfolio", back_populates="trade_orders")


class FiiDiiData(Base):
    __tablename__ = "fii_dii_data"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    participant_type = Column(String(5), nullable=False)  # FII | DII
    buy_value_cr = Column(Float, nullable=True, default=0.0)
    sell_value_cr = Column(Float, nullable=True, default=0.0)
    net_value_cr = Column(Float, nullable=True, default=0.0)
    oi_contracts = Column(BigInteger, nullable=True, default=0)

    __table_args__ = (
        UniqueConstraint("trade_date", "participant_type", name="uix_fii_dii_date_type"),
    )
