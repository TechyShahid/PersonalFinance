"""
Quantitative Screening Engine.
Implements multi-gate institutional accumulation pattern detection
for identifying high-probability swing trade candidates.
"""

import math
from datetime import date, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import DailyEodData, ScreeningResult
from app.services.ingestion import (
    compute_ema,
    compute_atr,
    compute_delivery_avg,
    compute_volume_avg,
    compute_rolling_std,
)


# ─── Screening Gate Functions ──────────────────────────────────────────────────

def liquidity_gate(turnover_cr: float, cap_category: str = "MIDCAP", threshold: Optional[float] = None) -> bool:
    """
    Gate 1: Minimum daily turnover in crores.
    Dynamic thresholds based on market cap:
    - Smallcap: >= 5 Cr
    - Midcap: >= 15 Cr
    - Largecap: >= 30 Cr
    """
    if threshold is None:
        if cap_category == "SMALLCAP":
            threshold = 5.0
        elif cap_category == "MIDCAP":
            threshold = 15.0
        else:
            threshold = 30.0
    return turnover_cr >= threshold


def delivery_footprint_gate(
    deliverable_qty: int,
    avg_delivery_20d: Optional[float],
    delivery_pct: float,
    delivery_multiplier: float = 2.0,
    min_delivery_pct: float = 55.0,
) -> bool:
    """Gate 2: Deliverable volume > 2x 20-day average AND delivery% >= 55%."""
    if avg_delivery_20d is None or avg_delivery_20d == 0:
        return False
    return (
        deliverable_qty > delivery_multiplier * avg_delivery_20d
        and delivery_pct >= min_delivery_pct
    )


def price_confirmation_gate(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    ema_20: Optional[float],
    ema_50: Optional[float],
) -> bool:
    """
    Gate 3: Green candle + close in top 25% of range + above 20/50 EMA.
    """
    if ema_20 is None or ema_50 is None:
        return False

    # Green candle
    if close_price <= open_price:
        return False

    # Close in top 25% of daily range
    daily_range = high_price - low_price
    if daily_range == 0:
        return False
    close_position = (close_price - low_price) / daily_range
    if close_position < 0.75:
        return False

    # Above both EMAs
    if close_price < ema_20 or close_price < ema_50:
        return False

    return True


# ─── Pattern Detection ─────────────────────────────────────────────────────────

def detect_vcp(
    closes: List[float],
    atrs: List[Optional[float]],
    lookback: int = 60,
) -> Tuple[bool, float]:
    """
    Volatility Contraction Pattern (VCP) Detection.
    Looks for rolling std deviation contracting over 3+ periods
    and ATR dropping >= 15% from recent peak.
    Returns (is_vcp, vcp_score 0-100).
    """
    if len(closes) < lookback:
        return False, 0.0

    recent_closes = closes[-lookback:]
    stds = compute_rolling_std(recent_closes, 20)

    # Check for contraction: divide into 3 periods
    valid_stds = [s for s in stds if s is not None]
    if len(valid_stds) < 15:
        return False, 0.0

    third = len(valid_stds) // 3
    period_1_avg = sum(valid_stds[:third]) / third
    period_2_avg = sum(valid_stds[third : 2 * third]) / third
    period_3_avg = sum(valid_stds[2 * third :]) / (len(valid_stds) - 2 * third)

    # Contracting: each subsequent period should have lower avg std
    contracting = period_1_avg > period_2_avg > period_3_avg

    # ATR drop check
    valid_atrs = [a for a in atrs[-lookback:] if a is not None]
    atr_dropping = False
    atr_score = 0.0
    if len(valid_atrs) >= 20:
        peak_atr = max(valid_atrs[:len(valid_atrs) // 2])
        recent_atr = valid_atrs[-1]
        if peak_atr > 0:
            atr_drop_pct = (peak_atr - recent_atr) / peak_atr
            atr_dropping = atr_drop_pct >= 0.15
            atr_score = min(atr_drop_pct * 100, 50)

    if not contracting and not atr_dropping:
        return False, 0.0

    # Score: weight contraction and ATR drop
    contraction_score = 0.0
    if contracting and period_1_avg > 0:
        contraction_ratio = 1 - (period_3_avg / period_1_avg)
        contraction_score = min(contraction_ratio * 100, 50)

    vcp_score = contraction_score + atr_score
    is_vcp = vcp_score >= 30

    return is_vcp, round(min(vcp_score, 100), 1)


def detect_accumulation_cluster(
    delivery_pcts: List[float],
    volumes: List[int],
    avg_volume_20d: Optional[float],
    min_days: int = 5,
    min_delivery_pct: float = 50.0,
    max_volume_ratio: float = 1.5,
) -> Tuple[bool, float]:
    """
    Multi-session quiet accumulation cluster detection.
    5+ consecutive days with delivery% >= 50% and volume below 1.5x average.
    """
    if avg_volume_20d is None or avg_volume_20d == 0:
        return False, 0.0

    if len(delivery_pcts) < min_days:
        return False, 0.0

    # Check last 10 sessions for accumulation cluster
    lookback = min(10, len(delivery_pcts))
    recent_delivery = delivery_pcts[-lookback:]
    recent_volume = volumes[-lookback:]

    consecutive = 0
    max_consecutive = 0
    for i in range(len(recent_delivery)):
        if (
            recent_delivery[i] >= min_delivery_pct
            and recent_volume[i] <= max_volume_ratio * avg_volume_20d
        ):
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0

    is_accumulation = max_consecutive >= min_days
    score = min((max_consecutive / min_days) * 60, 80) if max_consecutive >= 3 else 0
    return is_accumulation, round(score, 1)


def detect_ema_pullback(
    close_price: float,
    ema_20: Optional[float],
    volume: int,
    avg_volume_20d: Optional[float],
    proximity_pct: float = 1.5,
    dry_volume_ratio: float = 0.7,
) -> Tuple[bool, float]:
    """
    Pullback to 20-day EMA with dry volume.
    Price within 1.5% of 20 EMA, volume <= 0.7x average.
    """
    if ema_20 is None or ema_20 == 0 or avg_volume_20d is None or avg_volume_20d == 0:
        return False, 0.0

    price_distance_pct = abs(close_price - ema_20) / ema_20 * 100
    is_near_ema = price_distance_pct <= proximity_pct
    is_dry_volume = volume <= dry_volume_ratio * avg_volume_20d

    if is_near_ema and is_dry_volume:
        # Score based on how close to EMA and how dry the volume
        ema_score = max(0, (proximity_pct - price_distance_pct) / proximity_pct * 50)
        vol_score = max(0, (dry_volume_ratio - (volume / avg_volume_20d)) / dry_volume_ratio * 50) if avg_volume_20d > 0 else 0
        return True, round(ema_score + vol_score, 1)

    return False, 0.0


# ─── Risk-Reward Calculation ───────────────────────────────────────────────────

def calculate_risk_reward(
    entry_price: float,
    recent_lows: List[float],
    default_stop_pct: float = 0.05,
) -> Dict:
    """Calculate entry, stop-loss, and 2R target."""
    # Stop at max(recent swing low, 5% below entry)
    swing_low = min(recent_lows[-5:]) if len(recent_lows) >= 5 else entry_price * (1 - default_stop_pct)
    hard_stop = entry_price * (1 - default_stop_pct)
    stop_loss = max(swing_low, hard_stop)

    risk = entry_price - stop_loss
    if risk <= 0:
        risk = entry_price * 0.04  # Fallback 4% risk
        stop_loss = entry_price - risk

    target = entry_price + 2 * risk
    rr_ratio = 2.0 if risk > 0 else 0

    return {
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "target_price": round(target, 2),
        "risk": round(risk, 2),
        "reward": round(2 * risk, 2),
        "risk_reward_ratio": round(rr_ratio, 1),
    }


# ─── Composite Scoring ────────────────────────────────────────────────────────

def compute_composite_score(
    liquidity_pass: bool,
    delivery_pass: bool,
    price_pass: bool,
    vcp_score: float,
    accumulation_score: float,
    pullback_score: float,
    delivery_pct: float,
    turnover_cr: float,
) -> float:
    """
    Weighted composite score (0–100) combining all screening gates.
    """
    score = 0.0

    # Gate scores (must-pass gates contribute base points)
    if liquidity_pass:
        score += 15
    if delivery_pass:
        score += 20
    if price_pass:
        score += 15

    # Pattern scores (best pattern)
    best_pattern_score = max(vcp_score, accumulation_score, pullback_score)
    score += best_pattern_score * 0.35

    # Delivery % bonus (above 60% gets extra points)
    if delivery_pct >= 70:
        score += 10
    elif delivery_pct >= 60:
        score += 5

    # Turnover strength bonus
    if turnover_cr >= 100:
        score += 5
    elif turnover_cr >= 50:
        score += 3

    return round(min(score, 100), 1)


# ─── Build Rationale ──────────────────────────────────────────────────────────

def build_rationale(
    symbol: str,
    liquidity_pass: bool,
    delivery_pass: bool,
    price_pass: bool,
    is_vcp: bool,
    vcp_score: float,
    is_accumulation: bool,
    acc_score: float,
    is_pullback: bool,
    pullback_score: float,
    delivery_pct: float,
    turnover_cr: float,
) -> str:
    """Build human-readable screening rationale."""
    parts = [f"[{symbol}]"]

    if liquidity_pass:
        parts.append(f"Turnover ₹{turnover_cr:.0f}Cr passes liquidity gate.")
    if delivery_pass:
        parts.append(f"Delivery {delivery_pct:.1f}% shows institutional interest.")
    if price_pass:
        parts.append("Strong green candle closing near high, above key EMAs.")

    patterns = []
    if is_vcp:
        patterns.append(f"VCP detected (score: {vcp_score:.0f})")
    if is_accumulation:
        patterns.append(f"Quiet accumulation cluster (score: {acc_score:.0f})")
    if is_pullback:
        patterns.append(f"Dry pullback to 20 EMA (score: {pullback_score:.0f})")

    if patterns:
        parts.append("Patterns: " + "; ".join(patterns) + ".")

    return " ".join(parts)


# ─── Main Screening Pipeline ──────────────────────────────────────────────────

def run_screening(db: Session, scan_date: Optional[date] = None) -> List[ScreeningResult]:
    """
    Execute the full multi-gate screening pipeline on all symbols.
    Returns scored candidates saved to the database.
    """
    from app.seed import STOCK_UNIVERSE

    if scan_date is None:
        scan_date = date.today()

    # Clear previous results for this date
    db.query(ScreeningResult).filter(ScreeningResult.scan_date == scan_date).delete()

    # Get all symbols
    symbols = db.query(DailyEodData.symbol).distinct().all()
    candidates = []

    for (symbol,) in symbols:
        # Fetch last 120 days of data
        history = (
            db.query(DailyEodData)
            .filter(DailyEodData.symbol == symbol)
            .order_by(DailyEodData.trade_date.asc())
            .all()
        )

        if len(history) < 20:
            continue

        stock_info = STOCK_UNIVERSE.get(symbol, {})
        cap_category = stock_info.get("cap", "MIDCAP")
        market_cap_cr = stock_info.get("mcap_cr", 10000.0)
        sector = stock_info.get("sector", "Diversified")

        latest = history[-1]
        closes = [h.close_price for h in history]
        highs = [h.high_price for h in history]
        lows = [h.low_price for h in history]
        volumes = [h.total_traded_qty for h in history]
        deliveries = [h.deliverable_qty or 0 for h in history]
        delivery_pcts = [h.delivery_pct or 0 for h in history]
        atrs = [h.atr_14 for h in history]

        # Compute rolling averages
        delivery_avgs = compute_delivery_avg(deliveries)
        volume_avgs = compute_volume_avg(volumes)

        avg_delivery_20d = delivery_avgs[-1] if delivery_avgs else None
        avg_volume_20d = volume_avgs[-1] if volume_avgs else None

        # ── Gate 1: Dynamic Liquidity ──
        liq_pass = liquidity_gate(latest.turnover_cr or 0, cap_category=cap_category)

        # ── Gate 2: Delivery Footprint ──
        del_pass = delivery_footprint_gate(
            latest.deliverable_qty or 0,
            avg_delivery_20d,
            latest.delivery_pct or 0,
        )

        # ── Gate 3: Price Confirmation ──
        price_pass = price_confirmation_gate(
            latest.open_price,
            latest.high_price,
            latest.low_price,
            latest.close_price,
            latest.ema_20,
            latest.ema_50,
        )

        # Skip if no gates pass
        if not (liq_pass or del_pass or price_pass):
            continue

        # ── Pattern Detection ──
        is_vcp, vcp_score = detect_vcp(closes, atrs)
        is_accumulation, acc_score = detect_accumulation_cluster(
            delivery_pcts, volumes, avg_volume_20d
        )
        is_pullback, pullback_score = detect_ema_pullback(
            latest.close_price, latest.ema_20, latest.total_traded_qty, avg_volume_20d
        )

        # ── Composite Score ──
        composite = compute_composite_score(
            liq_pass, del_pass, price_pass,
            vcp_score, acc_score, pullback_score,
            latest.delivery_pct or 0,
            latest.turnover_cr or 0,
        )

        # Only keep candidates with score >= 40
        if composite < 40:
            continue

        # Determine best setup type
        pattern_scores = {
            "VCP": vcp_score,
            "EMA_PULLBACK": pullback_score,
            "ACCUMULATION": acc_score,
        }
        setup_type = max(pattern_scores, key=pattern_scores.get)

        # Risk-Reward calculation
        rr = calculate_risk_reward(latest.close_price, lows)

        # Build rationale
        rationale = build_rationale(
            symbol, liq_pass, del_pass, price_pass,
            is_vcp, vcp_score, is_accumulation, acc_score,
            is_pullback, pullback_score,
            latest.delivery_pct or 0, latest.turnover_cr or 0,
        )

        # Save result
        result = ScreeningResult(
            symbol=symbol,
            scan_date=scan_date,
            composite_score=composite,
            setup_type=setup_type,
            delivery_pct=latest.delivery_pct,
            turnover_cr=latest.turnover_cr,
            risk_reward_ratio=rr["risk_reward_ratio"],
            entry_price=rr["entry_price"],
            stop_loss=rr["stop_loss"],
            target_price=rr["target_price"],
            rationale=rationale,
            cap_category=cap_category,
            market_cap_cr=market_cap_cr,
            sector=sector,
            is_active=True,
        )
        db.add(result)
        candidates.append(result)

    db.commit()

    # Sort by composite score descending
    candidates.sort(key=lambda c: c.composite_score, reverse=True)
    return candidates


def get_screening_results(
    db: Session,
    scan_date: Optional[date] = None,
    min_score: float = 0,
    setup_type: Optional[str] = None,
    cap_category: Optional[str] = None,
    limit: int = 50,
) -> List[ScreeningResult]:
    """Fetch screening results with optional market cap and setup filters."""
    query = db.query(ScreeningResult)

    if scan_date:
        query = query.filter(ScreeningResult.scan_date == scan_date)
    if min_score > 0:
        query = query.filter(ScreeningResult.composite_score >= min_score)
    if setup_type:
        query = query.filter(ScreeningResult.setup_type == setup_type)

    # Market Cap segment filtering
    if cap_category:
        cap_clean = cap_category.upper().strip()
        if cap_clean in ["MID_SMALL", "MID_AND_SMALL", "MIDSMALL"]:
            query = query.filter(ScreeningResult.cap_category.in_(["MIDCAP", "SMALLCAP"]))
        elif cap_clean in ["SMALLCAP", "MIDCAP", "LARGECAP"]:
            query = query.filter(ScreeningResult.cap_category == cap_clean)
        # If "ALL", no filter applied

    return (
        query.filter(ScreeningResult.is_active == True)
        .order_by(ScreeningResult.composite_score.desc())
        .limit(limit)
        .all()
    )
