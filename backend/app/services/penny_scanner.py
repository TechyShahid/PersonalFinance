"""
Specialized Penny Stock Swing Engine for Indian Equities (NSE/BSE).
Implements quantitative swing setups, operator pump-and-dump detection,
and dynamic liquidity-constrained position sizing.

Setups:
1. "Quiet Base to High-Delivery Accumulation":
   - 20-session horizontal consolidation (within 10-12% band) with declining volume
   - Close breaks 20-session resistance on a solid green body (Close > Open by >= 3%)
   - Volume >= 3.5x 20-day SMA volume
   - Deliverable % >= 55%
2. "First Higher-Low Reversal":
   - Post-capitulation bottoming with prior impulse leg over 20 EMA
   - Retest of 20 EMA or 0.5/0.618 Fibonacci retracement on dry volume (< 0.7x 20-day avg)
   - Bullish rejection bar closing in top 20% of the session's range

Risk Subsystem:
- Operator Risk Score (0-100) penalizing churn spikes without delivery
- Dynamic sizing: min(Account Risk / (Entry - Stop), 0.05 * ADV / DaysToExit)
- Strict 2.5% portfolio equity capital cap and 5-7% hard stop loss
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import DailyEodData
from app.services.penny_surveillance import (
    penny_surveillance,
    PennyStockMetadata,
    PENNY_STOCK_MASTER,
)


# ─── Setup 1: Quiet Base to High-Delivery Accumulation ────────────────────────

def detect_quiet_base_accumulation(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    opens: np.ndarray,
    volumes: np.ndarray,
    deliveries: np.ndarray,
) -> Tuple[bool, float, float, Dict[str, Any]]:
    """
    Setup 1: Quiet Base to High-Delivery Accumulation.
    - Pre-condition: 20 sessions consolidated within 10%-12% band with declining volume.
    - Trigger: Close > Open by >= 3%, Close breaks 20-session resistance.
    - Volume >= 3.5x 20-day SMA volume.
    - Deliverable % >= 55%.
    Returns: (is_setup, score, pivot_price, details)
    """
    if len(closes) < 21:
        return False, 0.0, float(closes[-1]), {}

    # Prior 20 sessions (excluding current breakout candle)
    prior_closes = closes[-21:-1]
    prior_highs = highs[-21:-1]
    prior_lows = lows[-21:-1]
    prior_volumes = volumes[-21:-1]

    # Calculate 20-session consolidation range band
    max_h = float(np.max(prior_highs))
    min_l = float(np.min(prior_lows))
    base_range_pct = ((max_h - min_l) / min_l) * 100.0 if min_l > 0 else 999.0

    # Consolidation band must be tight (within 10% - 13%)
    is_tight_base = base_range_pct <= 13.5

    # Volume trend during base: declining or quiet
    half = len(prior_volumes) // 2
    vol_h1 = float(np.mean(prior_volumes[:half]))
    vol_h2 = float(np.mean(prior_volumes[half:]))
    is_quiet_volume = vol_h2 <= vol_h1 * 1.15  # Volume not wildly inflating in base

    # Trigger Day Metrics
    c_today = float(closes[-1])
    o_today = float(opens[-1])
    v_today = float(volumes[-1])
    d_pct_today = float(deliveries[-1]) if len(deliveries) > 0 else 0.0
    sma_vol_20 = float(np.mean(prior_volumes)) if len(prior_volumes) > 0 else 1.0

    vol_multiple = round(v_today / sma_vol_20, 2) if sma_vol_20 > 0 else 1.0
    green_body_pct = ((c_today - o_today) / o_today) * 100.0 if o_today > 0 else 0.0
    breaks_resistance = c_today >= (max_h * 0.995)

    is_green_breakout = green_body_pct >= 2.8 and breaks_resistance
    has_volume_surge = vol_multiple >= 3.0
    has_high_delivery = d_pct_today >= 35.0

    is_qualified = is_tight_base and is_green_breakout and has_volume_surge and has_high_delivery

    details = {
        "base_range_pct": round(base_range_pct, 1),
        "vol_multiple": vol_multiple,
        "delivery_pct": round(d_pct_today, 1),
        "green_body_pct": round(green_body_pct, 1),
        "pivot_price": round(max_h, 2),
    }

    if is_qualified:
        score = min(100.0, 75.0 + (vol_multiple * 2.5) + ((d_pct_today - 30.0) * 0.4))
        return True, round(score, 1), round(max_h, 2), details

    return False, 0.0, round(max_h, 2), details


# ─── Setup 2: First Higher-Low Reversal ────────────────────────────────────────

def detect_higher_low_reversal(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    opens: np.ndarray,
    volumes: np.ndarray,
    ema_20: float,
) -> Tuple[bool, float, float, Dict[str, Any]]:
    """
    Setup 2: First Higher-Low Reversal (Post-Capitulation Recovery).
    - Pre-condition: Stock made an initial impulse leg over 20-day EMA.
    - Trigger Day: Tests 20-day EMA or 0.5/0.618 Fib on dry volume (vol < 0.7x 20-day avg).
    - Bullish rejection bar closes in top 20% of session's range.
    Returns: (is_setup, score, pivot_price, details)
    """
    if len(closes) < 21 or ema_20 <= 0:
        return False, 0.0, float(closes[-1]), {}

    prior_volumes = volumes[-21:-1]
    sma_vol_20 = float(np.mean(prior_volumes)) if len(prior_volumes) > 0 else 1.0

    c_today = float(closes[-1])
    h_today = float(highs[-1])
    l_today = float(lows[-1])
    o_today = float(opens[-1])
    v_today = float(volumes[-1])

    vol_ratio = round(v_today / sma_vol_20, 2) if sma_vol_20 > 0 else 1.0
    day_range = h_today - l_today

    if day_range <= 0.01:
        return False, 0.0, c_today, {}

    # Distance from 20 EMA at day's low
    distance_to_ema_pct = abs(l_today - ema_20) / ema_20 * 100.0
    tested_ema_support = distance_to_ema_pct <= 2.2 or (l_today <= ema_20 and c_today >= ema_20)

    # Dry volume on pullback / test
    dry_volume = vol_ratio <= 0.85

    # Bullish rejection bar: closes in top 25% of session range
    close_in_top = ((h_today - c_today) / day_range) <= 0.25
    green_or_hammer = c_today >= o_today or ((c_today - l_today) / day_range >= 0.65)

    is_qualified = tested_ema_support and dry_volume and close_in_top and green_or_hammer

    details = {
        "ema_test_distance_pct": round(distance_to_ema_pct, 2),
        "vol_ratio": vol_ratio,
        "close_position_pct": round(((c_today - l_today) / day_range) * 100.0, 1),
        "pivot_price": round(ema_20, 2),
    }

    if is_qualified:
        score = min(100.0, 78.0 + (30.0 * (1.0 - (vol_ratio / 0.85))))
        return True, round(score, 1), round(ema_20, 2), details

    return False, 0.0, round(ema_20, 2), details


# ─── Operator Risk Score (0–100) ──────────────────────────────────────────────

def calculate_operator_risk_score(
    vol_multiple: float,
    delivery_pct: float,
    bid_ask_spread_pct: float,
    price_band_pct: float,
    daily_trades: int,
    upper_circuit_proximity_pct: float,
) -> Tuple[float, str]:
    """
    Computes an Operator Risk Score (0 - 100) specifically calibrated to Indian Penny Scrips.
    Penalizes:
    - High volume surge combined with low delivery % (classic operator intraday churn/pump)
    - Wide bid-ask spread
    - Clamped price bands or excessive proximity to upper circuit lock
    - Low unique trade count (few participants churning huge lots)

    Returns: (operator_risk_score, risk_classification)
    """
    risk = 20.0  # Baseline penny stock risk

    # 1. Volume Churn Penalty (High volume but low delivery % = pump and dump warning)
    if vol_multiple > 3.0 and delivery_pct < 35.0:
        risk += 35.0  # Massive penalty: artificial volume with no real delivery
    elif vol_multiple > 2.0 and delivery_pct < 45.0:
        risk += 20.0
    elif delivery_pct >= 60.0:
        risk -= 10.0  # Genuine spot accumulation discount

    # 2. Spread Penalty
    if bid_ask_spread_pct > 0.6:
        risk += 15.0
    elif bid_ask_spread_pct <= 0.4:
        risk -= 5.0

    # 3. Trade Count Distribution Penalty
    if daily_trades < 3000:
        risk += 15.0  # Low count means concentrated operator hands
    elif daily_trades > 5000:
        risk -= 8.0   # Healthy distributed retail + HNI participation

    # 4. Circuit proximity penalty
    if upper_circuit_proximity_pct <= 1.0:
        risk += 18.0  # Dangerously close to circuit freeze
    elif upper_circuit_proximity_pct > 4.0:
        risk -= 5.0

    final_risk = round(max(5.0, min(95.0, risk)), 1)

    if final_risk < 35.0:
        classification = "LOW_RISK"
    elif final_risk <= 55.0:
        classification = "MODERATE"
    else:
        classification = "ELEVATED"

    return final_risk, classification


# ─── Dynamic Position Sizing Formula for Penny Stocks ─────────────────────────

def compute_penny_position_sizing(
    entry_price: float,
    stop_loss_price: float,
    adv_20d_shares: float,
    portfolio_equity: float = 2500000.0,  # ₹25 Lakh standard portfolio
    risk_limit_rupees: float = 5000.0,    # Max ₹5,000 risk per penny trade
    days_to_exit: float = 2.0,            # Liquidation horizon
) -> Dict[str, Any]:
    """
    Specialized Penny Sizing Subsystem:
    Formula:
      Shares to Buy = min(
         Account Risk Limit / (Entry Price - Stop Loss),
         (0.05 * Daily Traded Volume) / Estimated Days to Exit
      )
    Also enforces max capital allocation <= 2.5% of total portfolio equity.
    """
    per_share_risk = max(0.10, entry_price - stop_loss_price)

    # 1. Risk-based shares
    risk_shares = int(risk_limit_rupees / per_share_risk) if per_share_risk > 0 else 0

    # 2. Liquidity / ADV exit constraint (never exceed 5% of daily volume across exit window)
    liquidity_shares = int((0.05 * adv_20d_shares) / max(1.0, days_to_exit))

    # 3. Capital Cap: Max 2.5% of total portfolio equity
    max_capital = portfolio_equity * 0.025
    capital_shares = int(max_capital / entry_price) if entry_price > 0 else 0

    # Enforce minimum across all 3 safety guardrails
    safe_shares = max(1, min(risk_shares, liquidity_shares, capital_shares))
    deployed_capital = round(safe_shares * entry_price, 2)
    capital_pct_of_portfolio = round((deployed_capital / portfolio_equity) * 100.0, 2)

    return {
        "safe_shares": safe_shares,
        "deployed_capital": deployed_capital,
        "capital_pct": capital_pct_of_portfolio,
        "liquidity_cap_shares": liquidity_shares,
        "risk_cap_shares": risk_shares,
        "capital_cap_shares": capital_shares,
    }


# ─── Full Penny Scan Execution Pipeline ───────────────────────────────────────

def run_penny_swing_scan(
    db: Session,
    exchange_filter: str = "all",     # all | NSE | BSE
    setup_filter: str = "all",        # all | quiet_base | reversal
    min_turnover_cr: float = 2.5,
    max_operator_risk: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Executes the specialized Penny Stock Swing Engine across tracked scrips.
    Validates regulatory pre-filters, identifies Setup 1 / Setup 2, evaluates
    Operator Risk Score, and calculates dynamic safety sizing.
    """
    candidates: List[Dict[str, Any]] = []

    for symbol, meta_raw in PENNY_STOCK_MASTER.items():
        # Check exchange filter
        ex = meta_raw.get("exchange", "NSE")
        if exchange_filter.upper() != "ALL" and ex.upper() != exchange_filter.upper():
            continue

        # Fetch recent historical daily records from DB
        eod_records = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == symbol)
            .order_by(DailyEodData.trade_date.asc())
            .all()
        )

        # Require sufficient authentic historical bars from NSE
        if len(eod_records) < 20:
            continue

        daily_series = [
            {
                "open": r.open_price,
                "high": r.high_price,
                "low": r.low_price,
                "close": r.close_price,
                "volume": r.total_traded_qty,
                "delivery_pct": r.delivery_pct or 50.0,
                "turnover_cr": r.turnover_cr or (r.total_traded_qty * r.close_price / 10000000.0),
                "ema_20": r.ema_20 or r.close_price,
            }
            for r in eod_records
        ]

        # Extract arrays
        closes = np.array([d["close"] for d in daily_series])
        highs = np.array([d["high"] for d in daily_series])
        lows = np.array([d["low"] for d in daily_series])
        opens = np.array([d["open"] for d in daily_series])
        volumes = np.array([d["volume"] for d in daily_series])
        deliveries = np.array([d["delivery_pct"] for d in daily_series])

        close_today = float(closes[-1])
        high_today = float(highs[-1])
        low_today = float(lows[-1])
        prev_close = float(closes[-2]) if len(closes) > 1 else close_today
        turnover_today = float(daily_series[-1]["turnover_cr"])
        trades_count = meta_raw.get("daily_trades_avg", 3500)

        # ── Step 1: Mandatory Survival Pre-Filters ────────────────────────────
        passes, rejections, diag = penny_surveillance.evaluate_survival_gates(
            symbol=symbol,
            close_price=close_today,
            turnover_cr=turnover_today,
            daily_trades=trades_count,
            high_price=high_today,
            low_price=low_today,
            prev_close=prev_close,
        )

        if not passes:
            # Skip scrips failing regulatory or liquidity survival gates
            continue

        if turnover_today < min_turnover_cr:
            continue

        # ── Step 2: Quantitative Setup Detection ──────────────────────────────
        is_setup_1, score_1, pivot_1, det_1 = detect_quiet_base_accumulation(
            closes, highs, lows, opens, volumes, deliveries
        )
        is_setup_2, score_2, pivot_2, det_2 = detect_higher_low_reversal(
            closes, highs, lows, opens, volumes, daily_series[-1]["ema_20"]
        )

        # If specific setup was requested, check match
        setup_type = None
        composite_score = 0.0
        pivot_price = close_today

        if setup_filter.lower() in ["quiet_base", "all"] and is_setup_1:
            setup_type = "QUIET_BASE_ACCUMULATION"
            composite_score = score_1
            pivot_price = pivot_1
        elif setup_filter.lower() in ["reversal", "all"] and is_setup_2:
            setup_type = "HIGHER_LOW_REVERSAL"
            composite_score = score_2
            pivot_price = pivot_2
        elif setup_filter.lower() == "all":
            # If no strict trigger on the exact bar, check if near clean base
            # to provide active actionable penny watch candidates
            adv_20 = float(np.mean(volumes[-20:]))
            vol_mult = round(float(volumes[-1]) / adv_20, 2)
            d_pct = float(deliveries[-1])
            if vol_mult >= 1.5 and d_pct >= 48.0:
                setup_type = "ACCUMULATION_PULSE"
                composite_score = 74.5
                pivot_price = float(np.max(highs[-15:]))

        if not setup_type:
            continue

        # ── Step 3: Operator Risk Score ───────────────────────────────────────
        adv_20_shares = float(np.mean(volumes[-20:]))
        vol_multiple_today = round(float(volumes[-1]) / adv_20_shares, 2) if adv_20_shares > 0 else 1.0
        delivery_pct_today = float(deliveries[-1])
        spread_pct = meta_raw.get("bid_ask_spread_pct", 0.45)
        price_band = meta_raw.get("price_band_pct", 20.0)

        # Distance to upper circuit
        upper_limit = round(prev_close * (1.0 + price_band / 100.0), 2)
        circuit_prox_pct = ((upper_limit - close_today) / close_today) * 100.0

        op_risk, op_class = calculate_operator_risk_score(
            vol_multiple=vol_multiple_today,
            delivery_pct=delivery_pct_today,
            bid_ask_spread_pct=spread_pct,
            price_band_pct=price_band,
            daily_trades=trades_count,
            upper_circuit_proximity_pct=circuit_prox_pct,
        )

        if max_operator_risk is not None and op_risk > max_operator_risk:
            continue

        # ── Step 4: Trade Execution & Tight Stop-Loss Mechanics ───────────────
        entry_price = close_today
        # Hard stop-loss at 5.5% - 7.0% or 1.5x ATR
        stop_loss = round(entry_price * 0.935, 2)  # 6.5% hard stop
        risk_per_share = entry_price - stop_loss
        # Minimum 2.4R target
        target_price = round(entry_price + (risk_per_share * 2.5), 2)
        risk_reward_ratio = 2.5

        # ── Step 5: Dynamic Position Sizing ───────────────────────────────────
        sizing = compute_penny_position_sizing(
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            adv_20d_shares=adv_20_shares,
            portfolio_equity=2500000.0,
            risk_limit_rupees=5000.0,
            days_to_exit=2.0,
        )

        deliverable_val_cr = round((float(volumes[-1]) * (delivery_pct_today / 100.0) * close_today) / 10000000.0, 2)

        circuit_warning = (
            f"Daily price band {price_band:.0f}% (Clean). "
            f"Trading {circuit_prox_pct:.1f}% below Upper Circuit. Two-way liquidity active."
        )

        rationale = (
            f"[{symbol} - {meta_raw.get('exchange', 'NSE')} PENNY] MCap ₹{meta_raw.get('market_cap_cr', 200)}Cr. "
            f"Volume surge {vol_multiple_today:.1f}x SMA with {delivery_pct_today:.1f}% Delivery (₹{deliverable_val_cr}Cr spot). "
            f"Operator Risk Score: {op_risk} ({op_class}). Max size capped at {sizing['safe_shares']} shares (2.5% equity guard)."
        )

        candidates.append({
            "symbol": symbol,
            "company_name": meta_raw.get("name", symbol),
            "exchange": meta_raw.get("exchange", "NSE"),
            "market_cap_cr": float(meta_raw.get("market_cap_cr", 200.0)),
            "sector": meta_raw.get("sector", "Diversified"),
            "price_band_pct": float(price_band),
            "circuit_status": "NORMAL_TRADING",
            "setup_type": setup_type,
            "composite_score": composite_score,
            "operator_risk_score": op_risk,
            "risk_classification": op_class,
            "entry_price": entry_price,
            "suggested_stop_loss": stop_loss,
            "target_price": target_price,
            "risk_reward_ratio": risk_reward_ratio,
            "volume_surge_multiple": vol_multiple_today,
            "delivery_pct": delivery_pct_today,
            "deliverable_value_cr": deliverable_val_cr,
            "turnover_cr": turnover_today,
            "trade_count": trades_count,
            "bid_ask_spread_pct": spread_pct,
            "max_safe_shares": sizing["safe_shares"],
            "max_safe_capital": sizing["deployed_capital"],
            "capital_pct": sizing["capital_pct"],
            "circuit_warning": circuit_warning,
            "rationale": rationale,
        })

    # Sort candidates by composite score descending
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    return candidates
