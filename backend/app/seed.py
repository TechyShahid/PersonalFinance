"""
Seed Data Generator.
Creates realistic synthetic NSE EOD data for 50 popular stocks,
a demo user with ₹25L capital, sample trades, and screening results.
"""

import random
import math
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.models import (
    User, Portfolio, Holding, DailyEodData, ScreeningResult,
    TradeOrder, FiiDiiData,
)
from app.services.ingestion import update_all_technicals


# ─── NSE Stock Universe ────────────────────────────────────────────────────────

STOCK_UNIVERSE = {
    # ── Large Caps (Nifty 50 / Next 50) ──
    "RELIANCE":   {"base": 2950, "vol": 0.018, "avg_vol": 8500000,  "sector": "Oil & Gas", "cap": "LARGECAP", "mcap_cr": 1980000},
    "TCS":        {"base": 3800, "vol": 0.015, "avg_vol": 3200000,  "sector": "IT", "cap": "LARGECAP", "mcap_cr": 1380000},
    "INFY":       {"base": 1650, "vol": 0.017, "avg_vol": 7500000,  "sector": "IT", "cap": "LARGECAP", "mcap_cr": 680000},
    "HDFCBANK":   {"base": 1720, "vol": 0.014, "avg_vol": 9800000,  "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 1310000},
    "ICICIBANK":  {"base": 1280, "vol": 0.016, "avg_vol": 12000000, "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 900000},
    "HINDUNILVR": {"base": 2480, "vol": 0.012, "avg_vol": 2800000,  "sector": "FMCG", "cap": "LARGECAP", "mcap_cr": 580000},
    "SBIN":       {"base": 820,  "vol": 0.020, "avg_vol": 18000000, "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 730000},
    "BHARTIARTL": {"base": 1580, "vol": 0.016, "avg_vol": 5500000,  "sector": "Telecom", "cap": "LARGECAP", "mcap_cr": 920000},
    "KOTAKBANK":  {"base": 1950, "vol": 0.015, "avg_vol": 3800000,  "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 385000},
    "ITC":        {"base": 465,  "vol": 0.014, "avg_vol": 14000000, "sector": "FMCG", "cap": "LARGECAP", "mcap_cr": 580000},
    "LT":         {"base": 3650, "vol": 0.018, "avg_vol": 2200000,  "sector": "Infra", "cap": "LARGECAP", "mcap_cr": 500000},
    "AXISBANK":   {"base": 1150, "vol": 0.019, "avg_vol": 10500000, "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 355000},
    "WIPRO":      {"base": 520,  "vol": 0.017, "avg_vol": 8200000,  "sector": "IT", "cap": "LARGECAP", "mcap_cr": 270000},
    "BAJFINANCE": {"base": 6950, "vol": 0.022, "avg_vol": 2800000,  "sector": "NBFC", "cap": "LARGECAP", "mcap_cr": 430000},
    "MARUTI":     {"base": 12500,"vol": 0.016, "avg_vol": 850000,   "sector": "Auto", "cap": "LARGECAP", "mcap_cr": 390000},
    "SUNPHARMA":  {"base": 1720, "vol": 0.017, "avg_vol": 4200000,  "sector": "Pharma", "cap": "LARGECAP", "mcap_cr": 412000},
    "TATAMOTORS": {"base": 980,  "vol": 0.024, "avg_vol": 15000000, "sector": "Auto", "cap": "LARGECAP", "mcap_cr": 325000},
    "TITAN":      {"base": 3650, "vol": 0.018, "avg_vol": 2100000,  "sector": "Consumer", "cap": "LARGECAP", "mcap_cr": 324000},
    "ULTRACEMCO": {"base": 11200,"vol": 0.015, "avg_vol": 520000,   "sector": "Cement", "cap": "LARGECAP", "mcap_cr": 323000},
    "ASIANPAINT": {"base": 2920, "vol": 0.016, "avg_vol": 1800000,  "sector": "Consumer", "cap": "LARGECAP", "mcap_cr": 280000},
    "NESTLEIND":  {"base": 2480, "vol": 0.013, "avg_vol": 420000,   "sector": "FMCG", "cap": "LARGECAP", "mcap_cr": 239000},
    "HCLTECH":    {"base": 1680, "vol": 0.017, "avg_vol": 4800000,  "sector": "IT", "cap": "LARGECAP", "mcap_cr": 455000},
    "TECHM":      {"base": 1560, "vol": 0.020, "avg_vol": 3500000,  "sector": "IT", "cap": "LARGECAP", "mcap_cr": 153000},
    "POWERGRID":  {"base": 310,  "vol": 0.015, "avg_vol": 12000000, "sector": "Power", "cap": "LARGECAP", "mcap_cr": 288000},
    "NTPC":       {"base": 380,  "vol": 0.016, "avg_vol": 15000000, "sector": "Power", "cap": "LARGECAP", "mcap_cr": 368000},
    "TATASTEEL":  {"base": 155,  "vol": 0.025, "avg_vol": 25000000, "sector": "Metals", "cap": "LARGECAP", "mcap_cr": 193000},
    "COALINDIA":  {"base": 485,  "vol": 0.018, "avg_vol": 8500000,  "sector": "Mining", "cap": "LARGECAP", "mcap_cr": 298000},
    "ADANIENT":   {"base": 3200, "vol": 0.028, "avg_vol": 3200000,  "sector": "Infra", "cap": "LARGECAP", "mcap_cr": 364000},
    "ADANIPORTS": {"base": 1380, "vol": 0.022, "avg_vol": 4500000,  "sector": "Infra", "cap": "LARGECAP", "mcap_cr": 298000},
    "ONGC":       {"base": 275,  "vol": 0.019, "avg_vol": 16000000, "sector": "Oil & Gas", "cap": "LARGECAP", "mcap_cr": 346000},
    "JSWSTEEL":   {"base": 920,  "vol": 0.023, "avg_vol": 5500000,  "sector": "Metals", "cap": "LARGECAP", "mcap_cr": 225000},
    "DRREDDY":    {"base": 6200, "vol": 0.016, "avg_vol": 850000,   "sector": "Pharma", "cap": "LARGECAP", "mcap_cr": 103000},
    "CIPLA":      {"base": 1480, "vol": 0.017, "avg_vol": 3200000,  "sector": "Pharma", "cap": "LARGECAP", "mcap_cr": 119000},
    "DIVISLAB":   {"base": 4850, "vol": 0.019, "avg_vol": 680000,   "sector": "Pharma", "cap": "LARGECAP", "mcap_cr": 128000},
    "BPCL":       {"base": 610,  "vol": 0.020, "avg_vol": 7800000,  "sector": "Oil & Gas", "cap": "LARGECAP", "mcap_cr": 132000},
    "GRASIM":     {"base": 2650, "vol": 0.018, "avg_vol": 1200000,  "sector": "Cement", "cap": "LARGECAP", "mcap_cr": 178000},
    "BAJAJFINSV": {"base": 1720, "vol": 0.021, "avg_vol": 2100000,  "sector": "NBFC", "cap": "LARGECAP", "mcap_cr": 274000},
    "HEROMOTOCO": {"base": 5200, "vol": 0.017, "avg_vol": 850000,   "sector": "Auto", "cap": "LARGECAP", "mcap_cr": 104000},
    "EICHERMOT":  {"base": 4850, "vol": 0.018, "avg_vol": 620000,   "sector": "Auto", "cap": "LARGECAP", "mcap_cr": 132000},
    "INDUSINDBK": {"base": 1480, "vol": 0.023, "avg_vol": 5500000,  "sector": "Banking", "cap": "LARGECAP", "mcap_cr": 115000},

    # ── High-Momentum Mid Caps (Nifty Midcap 150) ──
    "POLYCAB":    {"base": 6200, "vol": 0.022, "avg_vol": 620000,   "sector": "Electricals", "cap": "MIDCAP", "mcap_cr": 93000},
    "TRENT":      {"base": 6800, "vol": 0.026, "avg_vol": 1400000,  "sector": "Retail", "cap": "MIDCAP", "mcap_cr": 88000},
    "CUMMINSIND": {"base": 3400, "vol": 0.021, "avg_vol": 450000,   "sector": "Engineering", "cap": "MIDCAP", "mcap_cr": 47000},
    "DIXON":      {"base": 11800,"vol": 0.028, "avg_vol": 550000,   "sector": "Electronics & EMS", "cap": "MIDCAP", "mcap_cr": 70500},
    "PERSISTENT": {"base": 5200, "vol": 0.023, "avg_vol": 620000,   "sector": "IT", "cap": "MIDCAP", "mcap_cr": 40200},
    "COFORGE":    {"base": 7400, "vol": 0.025, "avg_vol": 480000,   "sector": "IT", "cap": "MIDCAP", "mcap_cr": 45600},
    "KAYNES":     {"base": 4950, "vol": 0.031, "avg_vol": 720000,   "sector": "Defense & EMS", "cap": "MIDCAP", "mcap_cr": 28900},
    "SUZLON":     {"base": 76,   "vol": 0.035, "avg_vol": 38000000, "sector": "Renewable Energy", "cap": "MIDCAP", "mcap_cr": 42500},
    "KPITTECH":   {"base": 1650, "vol": 0.026, "avg_vol": 1400000,  "sector": "Auto Tech", "cap": "MIDCAP", "mcap_cr": 33200},
    "FEDERALBNK": {"base": 198,  "vol": 0.020, "avg_vol": 9200000,  "sector": "Banking", "cap": "MIDCAP", "mcap_cr": 48500},
    "PRESTIGE":   {"base": 1820, "vol": 0.029, "avg_vol": 1200000,  "sector": "Real Estate", "cap": "MIDCAP", "mcap_cr": 36500},
    "HAL":        {"base": 4650, "vol": 0.027, "avg_vol": 1600000,  "sector": "Defense & Aerospace", "cap": "MIDCAP", "mcap_cr": 99500},
    "BEL":        {"base": 290,  "vol": 0.023, "avg_vol": 11000000, "sector": "Defense Electronics", "cap": "MIDCAP", "mcap_cr": 89000},
    "BHEL":       {"base": 295,  "vol": 0.031, "avg_vol": 14000000, "sector": "Capital Goods", "cap": "MIDCAP", "mcap_cr": 53000},
    "ZOMATO":     {"base": 260,  "vol": 0.029, "avg_vol": 24000000, "sector": "Tech", "cap": "MIDCAP", "mcap_cr": 81000},
    "PAYTM":      {"base": 870,  "vol": 0.033, "avg_vol": 9200000,  "sector": "Tech", "cap": "MIDCAP", "mcap_cr": 23000},

    # ── Explosive Small Caps (Nifty Smallcap 250 & Emerging Leaders) ──
    "DATAPATTNS": {"base": 3050, "vol": 0.033, "avg_vol": 420000,   "sector": "Defense Electronics", "cap": "SMALLCAP", "mcap_cr": 8450},
    "MAPMYINDIA": {"base": 2220, "vol": 0.030, "avg_vol": 320000,   "sector": "Tech & SaaS", "cap": "SMALLCAP", "mcap_cr": 5800},
    "CENTURYPLY": {"base": 795,  "vol": 0.024, "avg_vol": 490000,   "sector": "Building Materials", "cap": "SMALLCAP", "mcap_cr": 7600},
    "TEJASNET":   {"base": 1260, "vol": 0.034, "avg_vol": 580000,   "sector": "Telecom Equipment", "cap": "SMALLCAP", "mcap_cr": 10200},
    "GRAVITA":    {"base": 1890, "vol": 0.032, "avg_vol": 380000,   "sector": "Recycling & Green Energy", "cap": "SMALLCAP", "mcap_cr": 6400},
    "ELECON":     {"base": 1310, "vol": 0.029, "avg_vol": 450000,   "sector": "Industrial Machinery", "cap": "SMALLCAP", "mcap_cr": 7300},
    "NEWGEN":     {"base": 1210, "vol": 0.031, "avg_vol": 430000,   "sector": "Enterprise Software", "cap": "SMALLCAP", "mcap_cr": 8600},
    "ANANDRATHI": {"base": 3950, "vol": 0.028, "avg_vol": 280000,   "sector": "Wealth Management", "cap": "SMALLCAP", "mcap_cr": 7100},
    "NEULANDLAB": {"base": 12800,"vol": 0.034, "avg_vol": 140000,   "sector": "Pharma & API", "cap": "SMALLCAP", "mcap_cr": 8100},
    "TITAGARH":   {"base": 1490, "vol": 0.035, "avg_vol": 950000,   "sector": "Railways & Defense", "cap": "SMALLCAP", "mcap_cr": 9500},
    "JWL":        {"base": 525,  "vol": 0.033, "avg_vol": 1400000,  "sector": "Railways & Logistics", "cap": "SMALLCAP", "mcap_cr": 8100},
    "MARKSANS":   {"base": 255,  "vol": 0.030, "avg_vol": 2100000,  "sector": "Pharma", "cap": "SMALLCAP", "mcap_cr": 5100},
}


def _generate_price_series(base_price: float, volatility: float, days: int, trend: float = 0.0002) -> list:
    """Generate realistic price series with geometric Brownian motion."""
    prices = [base_price]
    for _ in range(days - 1):
        daily_return = random.gauss(trend, volatility)
        new_price = prices[-1] * math.exp(daily_return)
        prices.append(round(new_price, 2))
    return prices


def _generate_ohlcv(close_prices: list, avg_volume: int, volatility: float) -> list:
    """Generate OHLCV data from close prices."""
    records = []
    for i, close in enumerate(close_prices):
        # Generate intraday range
        range_pct = random.uniform(0.008, volatility * 3)
        half_range = close * range_pct / 2

        high = round(close + random.uniform(0, half_range * 1.5), 2)
        low = round(close - random.uniform(0, half_range * 1.5), 2)
        low = max(low, close * 0.92)  # Prevent unrealistic drops

        # Open: within the range, biased toward close
        open_price = round(low + random.uniform(0.3, 0.7) * (high - low), 2)

        # Volume with some variance
        vol_multiplier = random.uniform(0.5, 2.0)
        volume = int(avg_volume * vol_multiplier)

        # Delivery
        base_delivery_pct = random.uniform(30, 65)
        # Occasional high delivery days (institutional)
        if random.random() < 0.15:
            base_delivery_pct = random.uniform(60, 82)

        deliverable_qty = int(volume * base_delivery_pct / 100)
        avg_price = (high + low + close) / 3
        total_traded_value = volume * avg_price
        turnover_cr = round(total_traded_value / 1e7, 2)

        prev_close = close_prices[i - 1] if i > 0 else close * 0.99

        records.append({
            "open_price": open_price,
            "high_price": high,
            "low_price": low,
            "close_price": close,
            "last_price": close,
            "prev_close": round(prev_close, 2),
            "total_traded_qty": volume,
            "total_traded_value": round(total_traded_value, 2),
            "deliverable_qty": deliverable_qty,
            "delivery_pct": round(base_delivery_pct, 2),
            "turnover_cr": turnover_cr,
        })

    return records


def _get_trading_dates(start_date: date, num_days: int) -> list:
    """Generate trading dates (weekdays only, skip common holidays)."""
    dates = []
    current = start_date
    while len(dates) < num_days:
        if current.weekday() < 5:  # Mon-Fri
            dates.append(current)
        current += timedelta(days=1)
    return dates


def seed_eod_data(db: Session, days: int = 150) -> None:
    """Generate and insert synthetic EOD data for all stocks."""
    # Check if data already exists
    existing = db.query(DailyEodData).first()
    if existing:
        return

    end_date = date.today()
    start_date = end_date - timedelta(days=int(days * 1.5))  # Account for weekends
    trading_dates = _get_trading_dates(start_date, days)

    for symbol, config in STOCK_UNIVERSE.items():
        # Generate price series
        trend = random.uniform(-0.0001, 0.0005)  # Slight upward bias
        close_prices = _generate_price_series(
            config["base"], config["vol"], len(trading_dates), trend
        )

        # Generate full OHLCV
        ohlcv_data = _generate_ohlcv(close_prices, config["avg_vol"], config["vol"])

        # Insert into DB
        for i, trade_date in enumerate(trading_dates):
            record = ohlcv_data[i]
            eod = DailyEodData(
                symbol=symbol,
                series="EQ",
                trade_date=trade_date,
                **record,
            )
            db.add(eod)

    db.commit()

    # Compute technicals for all symbols
    update_all_technicals(db)


def seed_demo_user(db: Session) -> User:
    """Create a demo user with ₹25L capital and 70/30 portfolio split."""
    existing = db.query(User).filter(User.email == "demo@tradelab.in").first()
    if existing:
        return existing

    user = User(
        name="Shahid Khan",
        email="demo@tradelab.in",
        total_capital=2500000.0,
        core_allocation_pct=70.0,
        satellite_allocation_pct=30.0,
        max_concurrent_swings=6,
        max_risk_per_trade_pct=1.0,
    )
    db.add(user)
    db.flush()

    # Core portfolio (70% = ₹17.5L)
    core = Portfolio(
        user_id=user.id,
        portfolio_type="CORE",
        deployed_capital=1225000.0,  # 70% of 17.5L deployed
        cash_available=525000.0,
    )
    db.add(core)

    # Satellite portfolio (30% = ₹7.5L)
    satellite = Portfolio(
        user_id=user.id,
        portfolio_type="SATELLITE",
        deployed_capital=412500.0,  # ~55% deployed
        cash_available=337500.0,
    )
    db.add(satellite)
    db.flush()

    # ── Core Holdings (SIP compounders) ──
    core_holdings = [
        {"symbol": "HDFCBANK", "qty": 50, "avg": 1685.0},
        {"symbol": "TCS", "qty": 20, "avg": 3720.0},
        {"symbol": "RELIANCE", "qty": 30, "avg": 2890.0},
        {"symbol": "INFY", "qty": 60, "avg": 1610.0},
        {"symbol": "HINDUNILVR", "qty": 25, "avg": 2420.0},
    ]

    for h in core_holdings:
        latest_eod = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == h["symbol"])
            .order_by(DailyEodData.trade_date.desc())
            .first()
        )
        current = latest_eod.close_price if latest_eod else h["avg"] * 1.05

        holding = Holding(
            portfolio_id=core.id,
            symbol=h["symbol"],
            quantity=h["qty"],
            avg_buy_price=h["avg"],
            buy_date=date.today() - timedelta(days=random.randint(180, 450)),
            status="ACTIVE",
            current_price=current,
            unrealized_pnl=round((current - h["avg"]) * h["qty"], 2),
        )
        db.add(holding)

    # ── Active Swing Trades (Satellite) ──
    swing_symbols = ["TATAMOTORS", "BAJFINANCE", "TRENT", "POLYCAB"]
    for sym in swing_symbols:
        latest_eod = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == sym)
            .order_by(DailyEodData.trade_date.desc())
            .first()
        )
        if not latest_eod:
            continue

        entry = round(latest_eod.close_price * random.uniform(0.94, 0.99), 2)
        stop = round(entry * 0.95, 2)
        target = round(entry * 1.10, 2)
        qty = max(1, int(7500 / entry))  # ~₹7500 risk budget

        holding = Holding(
            portfolio_id=satellite.id,
            symbol=sym,
            quantity=qty,
            avg_buy_price=entry,
            buy_date=date.today() - timedelta(days=random.randint(3, 15)),
            status="ACTIVE",
            current_price=latest_eod.close_price,
            unrealized_pnl=round((latest_eod.close_price - entry) * qty, 2),
            stop_loss_price=stop,
            target_price=target,
        )
        db.add(holding)

        order = TradeOrder(
            user_id=user.id,
            portfolio_id=satellite.id,
            symbol=sym,
            order_type="BUY",
            status="OPEN",
            quantity=qty,
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            entry_date=datetime.utcnow() - timedelta(days=random.randint(3, 15)),
        )
        db.add(order)

    # ── Closed Trades (for journal) ──
    closed_symbols = [
        ("SBIN", True), ("AXISBANK", True), ("JSWSTEEL", False),
        ("SUNPHARMA", True), ("TECHM", True), ("CIPLA", False),
        ("COALINDIA", True), ("BPCL", True), ("INDUSINDBK", False),
        ("TATASTEEL", True), ("HEROMOTOCO", True), ("ADANIPORTS", False),
        ("ZOMATO", True), ("HCLTECH", True), ("NTPC", True),
    ]

    for sym, is_win in closed_symbols:
        latest_eod = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == sym)
            .order_by(DailyEodData.trade_date.desc())
            .first()
        )
        if not latest_eod:
            continue

        entry = round(latest_eod.close_price * random.uniform(0.88, 0.98), 2)
        hold_days = random.randint(5, 45)

        if is_win:
            exit_price = round(entry * random.uniform(1.06, 1.14), 2)
            status = "TARGET_REACHED"
        else:
            exit_price = round(entry * random.uniform(0.94, 0.98), 2)
            status = "STOP_TRIGGERED"

        qty = max(1, int(7500 / entry))
        pnl = round((exit_price - entry) * qty, 2)

        # Transaction costs (simplified for seed)
        buy_val = entry * qty
        sell_val = exit_price * qty
        total_val = buy_val + sell_val
        stt = round(total_val * 0.001, 2)
        brokerage = 40.0
        gst = round((brokerage + total_val * 0.0000345) * 0.18, 2)
        sebi = round(total_val * 0.000001, 2)
        stamp = round(buy_val * 0.00015, 2)
        exch = round(total_val * 0.0000345, 2)
        total_costs = stt + brokerage + gst + sebi + stamp + exch

        # Tax
        tax_type = "STCG" if hold_days < 365 else "LTCG"
        tax_amount = round(max(0, pnl) * 0.20, 2) if tax_type == "STCG" else round(max(0, pnl) * 0.125, 2)
        net_return = round(pnl - total_costs - tax_amount, 2)

        entry_date = datetime.utcnow() - timedelta(days=hold_days + random.randint(5, 30))
        exit_date = entry_date + timedelta(days=hold_days)

        order = TradeOrder(
            user_id=user.id,
            portfolio_id=satellite.id,
            symbol=sym,
            order_type="BUY",
            status="TAX_RECORDED",
            quantity=qty,
            entry_price=entry,
            stop_loss=round(entry * 0.95, 2),
            target_price=round(entry * 1.10, 2),
            exit_price=exit_price,
            entry_date=entry_date,
            exit_date=exit_date,
            realized_pnl=pnl,
            stt_paid=stt,
            gst_paid=gst,
            sebi_fee=sebi,
            brokerage=brokerage,
            stamp_duty=stamp,
            exchange_txn_charge=exch,
            tax_liability=tax_amount,
            tax_type=tax_type,
            net_return=net_return,
            notes=f"{'Target hit' if is_win else 'Stop triggered'} after {hold_days} days",
        )
        db.add(order)

    db.commit()
    return user


def seed_screening_results(db: Session) -> None:
    """Generate screening results for today."""
    existing = db.query(ScreeningResult).filter(
        ScreeningResult.scan_date == date.today()
    ).first()
    if existing:
        return

    candidates = [
        # Smallcaps
        {
            "symbol": "DATAPATTNS", "score": 88.5, "setup": "VCP",
            "delivery": 63.4, "turnover": 14.8, "rr": 2.8,
            "cap": "SMALLCAP", "mcap": 8450.0, "sector": "Defense Electronics",
            "rationale": "[DATAPATTNS] Smallcap Institutional Footprint. Turnover ₹15Cr exceeds ₹5Cr liquidity threshold. Delivery 63.4% indicates heavy accumulation into tight consolidation. VCP Stage 3 contraction."
        },
        {
            "symbol": "NEWGEN", "score": 84.1, "setup": "EMA_PULLBACK",
            "delivery": 61.5, "turnover": 11.2, "rr": 2.6,
            "cap": "SMALLCAP", "mcap": 8600.0, "sector": "Enterprise Software",
            "rationale": "[NEWGEN] Quality Smallcap SaaS compounder. Dry pullback to 20-day EMA with turnover ₹11Cr. Low float absorption pattern confirmed."
        },
        {
            "symbol": "TITAGARH", "score": 82.0, "setup": "ACCUMULATION",
            "delivery": 67.2, "turnover": 18.5, "rr": 2.5,
            "cap": "SMALLCAP", "mcap": 9500.0, "sector": "Railways & Defense",
            "rationale": "[TITAGARH] High Delivery% (67.2%) multi-day cluster. Railway capex theme leader breaking out of base with surging volume."
        },
        {
            "symbol": "MAPMYINDIA", "score": 79.4, "setup": "VCP",
            "delivery": 58.9, "turnover": 9.8, "rr": 2.4,
            "cap": "SMALLCAP", "mcap": 5800.0, "sector": "Tech & SaaS",
            "rationale": "[MAPMYINDIA] High-margin geospatial tech leader. Turnover ₹10Cr with 58.9% delivery. Contracting daily ranges prior to pivot breakout."
        },
        {
            "symbol": "ANANDRATHI", "score": 77.0, "setup": "EMA_PULLBACK",
            "delivery": 56.4, "turnover": 8.5, "rr": 2.2,
            "cap": "SMALLCAP", "mcap": 7100.0, "sector": "Wealth Management",
            "rationale": "[ANANDRATHI] Financialization of Indian savings tailwind. Dry volume pullback to ascending 20-day EMA with 1:2.2 R:R."
        },
        {
            "symbol": "ELECON", "score": 75.3, "setup": "ACCUMULATION",
            "delivery": 62.1, "turnover": 12.4, "rr": 2.3,
            "cap": "SMALLCAP", "mcap": 7300.0, "sector": "Industrial Machinery",
            "rationale": "[ELECON] Capital goods & defense supplier. 5-day delivery accumulation cluster with 62.1% deliverable volume."
        },

        # Midcaps
        {
            "symbol": "KAYNES", "score": 86.4, "setup": "VCP",
            "delivery": 66.8, "turnover": 42.5, "rr": 2.7,
            "cap": "MIDCAP", "mcap": 28900.0, "sector": "Defense & EMS",
            "rationale": "[KAYNES] High-beta Midcap EMS leader. Turnover ₹43Cr comfortably clears ₹15Cr midcap threshold. Delivery 66.8% showing massive institutional buying."
        },
        {
            "symbol": "DIXON", "score": 83.2, "setup": "ACCUMULATION",
            "delivery": 64.5, "turnover": 78.4, "rr": 2.5,
            "cap": "MIDCAP", "mcap": 70500.0, "sector": "Electronics & EMS",
            "rationale": "[DIXON] Electronics manufacturing leader. Quiet institutional accumulation cluster across 6 consecutive sessions with delivery >60%."
        },
        {
            "symbol": "TRENT", "score": 81.5, "setup": "VCP",
            "delivery": 71.8, "turnover": 185.6, "rr": 2.4,
            "cap": "MIDCAP", "mcap": 88000.0, "sector": "Retail",
            "rationale": "[TRENT] High-growth retail leader. Turnover ₹186Cr passes institutional liquidity gate. 71.8% delivery indicates relentless fund accumulation."
        },
        {
            "symbol": "POLYCAB", "score": 76.2, "setup": "EMA_PULLBACK",
            "delivery": 58.3, "turnover": 92.4, "rr": 2.1,
            "cap": "MIDCAP", "mcap": 93000.0, "sector": "Electricals",
            "rationale": "[POLYCAB] Wires & cables market leader. Textbook dry-volume pullback to 20-day EMA with excellent institutional sponsorship."
        },
        {
            "symbol": "PERSISTENT", "score": 74.8, "setup": "ACCUMULATION",
            "delivery": 61.2, "turnover": 65.0, "rr": 2.2,
            "cap": "MIDCAP", "mcap": 40200.0, "sector": "IT",
            "rationale": "[PERSISTENT] Top-tier Midcap IT outperformer. ₹65Cr turnover with 61.2% delivery, resilient against broader market swings."
        },
        {
            "symbol": "SUZLON", "score": 73.5, "setup": "VCP",
            "delivery": 59.4, "turnover": 125.0, "rr": 2.3,
            "cap": "MIDCAP", "mcap": 42500.0, "sector": "Renewable Energy",
            "rationale": "[SUZLON] Clean energy turnaround play. High liquidity ₹125Cr turnover with multi-week range contraction."
        },

        # Largecaps
        {
            "symbol": "TATAMOTORS", "score": 80.5, "setup": "VCP",
            "delivery": 68.2, "turnover": 485.3, "rr": 2.4,
            "cap": "LARGECAP", "mcap": 325000.0, "sector": "Auto",
            "rationale": "[TATAMOTORS] Turnover ₹485Cr passes liquidity gate. Delivery 68.2% shows institutional interest. Patterns: VCP detected (score: 72)."
        },
        {
            "symbol": "BAJFINANCE", "score": 78.9, "setup": "ACCUMULATION",
            "delivery": 62.5, "turnover": 320.8, "rr": 2.1,
            "cap": "LARGECAP", "mcap": 430000.0, "sector": "NBFC",
            "rationale": "[BAJFINANCE] Turnover ₹321Cr passes liquidity gate. Delivery 62.5% shows institutional interest. Strong green candle. Patterns: Quiet accumulation cluster."
        },
        {
            "symbol": "JSWSTEEL", "score": 70.8, "setup": "VCP",
            "delivery": 55.9, "turnover": 250.2, "rr": 2.2,
            "cap": "LARGECAP", "mcap": 225000.0, "sector": "Metals",
            "rationale": "[JSWSTEEL] Turnover ₹250Cr passes liquidity gate. Delivery 55.9%. Patterns: VCP detected (score: 58)."
        },
    ]

    for c in candidates:
        latest_eod = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == c["symbol"])
            .order_by(DailyEodData.trade_date.desc())
            .first()
        )

        stock_info = STOCK_UNIVERSE.get(c["symbol"], {})
        entry = latest_eod.close_price if latest_eod else float(stock_info.get("base", 1000.0))
        stop = round(entry * 0.95, 2)
        target = round(entry + 2 * (entry - stop), 2)

        result = ScreeningResult(
            symbol=c["symbol"],
            scan_date=date.today(),
            composite_score=c["score"],
            setup_type=c["setup"],
            delivery_pct=c["delivery"],
            turnover_cr=c["turnover"],
            risk_reward_ratio=c["rr"],
            entry_price=round(entry, 2),
            stop_loss=stop,
            target_price=target,
            rationale=c["rationale"],
            cap_category=c.get("cap", stock_info.get("cap", "MIDCAP")),
            market_cap_cr=c.get("mcap", stock_info.get("mcap_cr")),
            sector=c.get("sector", stock_info.get("sector")),
            is_active=True,
        )
        db.add(result)

    db.commit()


def seed_fii_dii_data(db: Session, days: int = 30) -> None:
    """Generate sample FII/DII data for the last 30 trading days."""
    existing = db.query(FiiDiiData).first()
    if existing:
        return

    end_date = date.today()
    start_date = end_date - timedelta(days=int(days * 1.5))
    trading_dates = _get_trading_dates(start_date, days)

    for td in trading_dates:
        # FII data
        fii_buy = round(random.uniform(8000, 18000), 2)
        fii_sell = round(random.uniform(7000, 17000), 2)
        fii = FiiDiiData(
            trade_date=td,
            participant_type="FII",
            buy_value_cr=fii_buy,
            sell_value_cr=fii_sell,
            net_value_cr=round(fii_buy - fii_sell, 2),
            oi_contracts=random.randint(500000, 2000000),
        )
        db.add(fii)

        # DII data
        dii_buy = round(random.uniform(6000, 14000), 2)
        dii_sell = round(random.uniform(5000, 12000), 2)
        dii = FiiDiiData(
            trade_date=td,
            participant_type="DII",
            buy_value_cr=dii_buy,
            sell_value_cr=dii_sell,
            net_value_cr=round(dii_buy - dii_sell, 2),
            oi_contracts=random.randint(300000, 1200000),
        )
        db.add(dii)

    db.commit()


def seed_all(db: Session) -> None:
    """Run all seed functions."""
    print("🌱 Seeding EOD data for 50 NSE stocks (150 trading days)...")
    seed_eod_data(db, days=150)

    print("👤 Creating demo user with ₹25L portfolio...")
    seed_demo_user(db)

    print("📊 Generating screening results...")
    seed_screening_results(db)

    print("🏦 Generating FII/DII data...")
    seed_fii_dii_data(db)

    print("✅ Seed complete!")
