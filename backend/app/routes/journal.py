"""
Trade Journal API Routes.
Historical trades, performance stats, and tax summaries.
"""

from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, TradeOrder
from app.schemas import TradeOrderResponse, JournalStatsResponse
from app.services.tax_engine import LTCG_EXEMPTION

router = APIRouter(prefix="/api/journal", tags=["Journal"])


@router.get("/trades", response_model=List[TradeOrderResponse])
def get_closed_trades(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get all closed/recorded trades."""
    user = db.query(User).first()
    if not user:
        return []

    return (
        db.query(TradeOrder)
        .filter(
            TradeOrder.user_id == user.id,
            TradeOrder.status.in_(["TAX_RECORDED", "CLOSED", "STOP_TRIGGERED", "TARGET_REACHED"]),
        )
        .order_by(TradeOrder.exit_date.desc())
        .limit(limit)
        .all()
    )


@router.get("/stats", response_model=JournalStatsResponse)
def get_journal_stats(db: Session = Depends(get_db)):
    """Get comprehensive trading statistics."""
    user = db.query(User).first()
    if not user:
        return JournalStatsResponse(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, avg_win_amount=0, avg_loss_amount=0,
            avg_hold_days=0, avg_r_multiple=0, max_drawdown=0,
            total_net_pnl=0, total_tax_paid=0, expectancy=0,
            stcg_total=0, ltcg_total=0,
            ltcg_exemption_used=0, ltcg_exemption_remaining=LTCG_EXEMPTION,
        )

    closed_trades = (
        db.query(TradeOrder)
        .filter(
            TradeOrder.user_id == user.id,
            TradeOrder.status == "TAX_RECORDED",
        )
        .all()
    )

    if not closed_trades:
        return JournalStatsResponse(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, avg_win_amount=0, avg_loss_amount=0,
            avg_hold_days=0, avg_r_multiple=0, max_drawdown=0,
            total_net_pnl=0, total_tax_paid=0, expectancy=0,
            stcg_total=0, ltcg_total=0,
            ltcg_exemption_used=0, ltcg_exemption_remaining=LTCG_EXEMPTION,
        )

    total = len(closed_trades)
    winners = [t for t in closed_trades if (t.realized_pnl or 0) > 0]
    losers = [t for t in closed_trades if (t.realized_pnl or 0) <= 0]

    win_count = len(winners)
    loss_count = len(losers)
    win_rate = round((win_count / total * 100) if total > 0 else 0, 1)

    avg_win = round(
        sum(t.realized_pnl for t in winners) / win_count if win_count > 0 else 0, 2
    )
    avg_loss = round(
        sum(t.realized_pnl for t in losers) / loss_count if loss_count > 0 else 0, 2
    )

    # Average hold time
    hold_days = []
    for t in closed_trades:
        if t.entry_date and t.exit_date:
            days = (t.exit_date - t.entry_date).days
            hold_days.append(days)
    avg_hold = round(sum(hold_days) / len(hold_days) if hold_days else 0, 1)

    # R-multiples
    r_multiples = []
    for t in closed_trades:
        if t.stop_loss and t.entry_price and t.realized_pnl is not None:
            risk_per_share = abs(t.entry_price - t.stop_loss)
            if risk_per_share > 0 and t.quantity > 0:
                r = t.realized_pnl / (risk_per_share * t.quantity)
                r_multiples.append(r)
    avg_r = round(sum(r_multiples) / len(r_multiples) if r_multiples else 0, 2)

    # Max drawdown (simplified)
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in sorted(closed_trades, key=lambda x: x.exit_date or x.entry_date):
        running_pnl += (t.net_return or 0)
        if running_pnl > peak:
            peak = running_pnl
        dd = peak - running_pnl
        if dd > max_dd:
            max_dd = dd

    # Totals
    total_net_pnl = round(sum(t.net_return or 0 for t in closed_trades), 2)
    total_tax = round(sum(t.tax_liability or 0 for t in closed_trades), 2)

    # Expectancy = (win_rate × avg_win) + (loss_rate × avg_loss)
    expectancy = round(
        (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss), 2
    )

    # Tax breakdown
    stcg_total = round(
        sum(t.tax_liability or 0 for t in closed_trades if t.tax_type == "STCG"), 2
    )
    ltcg_total = round(
        sum(t.tax_liability or 0 for t in closed_trades if t.tax_type == "LTCG"), 2
    )
    ltcg_gains = sum(
        t.realized_pnl or 0 for t in closed_trades
        if t.tax_type == "LTCG" and (t.realized_pnl or 0) > 0
    )
    ltcg_exemption_used = min(ltcg_gains, LTCG_EXEMPTION)
    ltcg_exemption_remaining = max(0, LTCG_EXEMPTION - ltcg_exemption_used)

    return JournalStatsResponse(
        total_trades=total,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=win_rate,
        avg_win_amount=avg_win,
        avg_loss_amount=avg_loss,
        avg_hold_days=avg_hold,
        avg_r_multiple=avg_r,
        max_drawdown=round(max_dd, 2),
        total_net_pnl=total_net_pnl,
        total_tax_paid=total_tax,
        expectancy=expectancy,
        stcg_total=stcg_total,
        ltcg_total=ltcg_total,
        ltcg_exemption_used=round(ltcg_exemption_used, 2),
        ltcg_exemption_remaining=round(ltcg_exemption_remaining, 2),
    )
