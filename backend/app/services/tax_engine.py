"""
Tax & Transaction Cost Engine for Indian Equity Markets.
Calculates STCG, LTCG, STT, GST, SEBI fees, exchange charges,
stamp duty, brokerage, and net real returns.
"""

from typing import Dict, Optional
from datetime import datetime


# ─── Tax Rate Constants (FY 2025-26 Budget rates) ─────────────────────────────

STCG_RATE = 0.20              # 20% Short-Term Capital Gains (equity)
LTCG_RATE = 0.125             # 12.5% Long-Term Capital Gains (equity)
LTCG_EXEMPTION = 125000.0     # ₹1.25L annual exemption threshold

# ─── Transaction Cost Constants ────────────────────────────────────────────────

STT_DELIVERY_RATE = 0.001     # 0.1% on both buy and sell (delivery)
EXCHANGE_TXN_RATE = 0.0000345 # 0.00345% NSE transaction charge
SEBI_TURNOVER_RATE = 0.000001 # 0.0001% SEBI turnover fee
GST_RATE = 0.18               # 18% GST on (brokerage + exchange charge + SEBI fee)
STAMP_DUTY_RATE = 0.00015     # 0.015% on buy side
DEFAULT_BROKERAGE = 20.0      # ₹20 per order (discount broker model)
BROKERAGE_PCT = 0.0003        # 0.03% (whichever is lower)

STCG_HOLDING_DAYS = 365       # < 365 days = STCG for equity


def classify_holding_period(holding_days: int) -> str:
    """Classify as STCG or LTCG based on holding period."""
    if holding_days < STCG_HOLDING_DAYS:
        return "STCG"
    return "LTCG"


def calculate_brokerage(trade_value: float, per_order: float = DEFAULT_BROKERAGE) -> float:
    """
    Calculate brokerage: min(₹20, 0.03% of trade value).
    Applied per order (buy and sell separately).
    """
    pct_brokerage = trade_value * BROKERAGE_PCT
    return round(min(per_order, pct_brokerage), 2)


def calculate_transaction_costs(
    buy_value: float,
    sell_value: float,
    brokerage_per_order: float = DEFAULT_BROKERAGE,
) -> Dict:
    """
    Calculate all transaction costs for a round-trip trade.

    Returns a detailed breakdown:
    - STT on buy + sell
    - Exchange transaction charge
    - SEBI turnover fee
    - GST on (brokerage + exchange + SEBI)
    - Stamp duty (buy side only)
    - Brokerage (buy + sell)
    """
    total_value = buy_value + sell_value

    # STT: 0.1% on both legs for delivery
    stt = round(total_value * STT_DELIVERY_RATE, 2)

    # Exchange transaction charge
    exchange_charge = round(total_value * EXCHANGE_TXN_RATE, 2)

    # SEBI turnover fee
    sebi_fee = round(total_value * SEBI_TURNOVER_RATE, 2)

    # Brokerage
    buy_brokerage = calculate_brokerage(buy_value, brokerage_per_order)
    sell_brokerage = calculate_brokerage(sell_value, brokerage_per_order)
    total_brokerage = round(buy_brokerage + sell_brokerage, 2)

    # GST: 18% on (brokerage + exchange charge + SEBI fee)
    gst_base = total_brokerage + exchange_charge + sebi_fee
    gst = round(gst_base * GST_RATE, 2)

    # Stamp duty: 0.015% on buy side only
    stamp_duty = round(buy_value * STAMP_DUTY_RATE, 2)

    total_costs = round(stt + exchange_charge + sebi_fee + gst + stamp_duty + total_brokerage, 2)

    return {
        "stt": stt,
        "exchange_txn_charge": exchange_charge,
        "sebi_fee": sebi_fee,
        "gst": gst,
        "stamp_duty": stamp_duty,
        "brokerage": total_brokerage,
        "total_transaction_costs": total_costs,
    }


def calculate_tax(
    gross_pnl: float,
    holding_days: int,
    ltcg_exemption_used: float = 0.0,
) -> Dict:
    """
    Calculate capital gains tax based on holding period.

    STCG (< 12 months): 20% flat
    LTCG (>= 12 months): 12.5% above ₹1.25L annual exemption
    """
    tax_type = classify_holding_period(holding_days)

    if gross_pnl <= 0:
        return {
            "tax_type": tax_type,
            "taxable_gain": 0.0,
            "tax_amount": 0.0,
            "exemption_used": 0.0,
        }

    if tax_type == "STCG":
        tax_amount = round(gross_pnl * STCG_RATE, 2)
        return {
            "tax_type": "STCG",
            "taxable_gain": round(gross_pnl, 2),
            "tax_amount": tax_amount,
            "exemption_used": 0.0,
        }

    # LTCG calculation with exemption
    remaining_exemption = max(0, LTCG_EXEMPTION - ltcg_exemption_used)
    taxable = max(0, gross_pnl - remaining_exemption)
    exemption_used = min(gross_pnl, remaining_exemption)
    tax_amount = round(taxable * LTCG_RATE, 2)

    return {
        "tax_type": "LTCG",
        "taxable_gain": round(taxable, 2),
        "tax_amount": tax_amount,
        "exemption_used": round(exemption_used, 2),
    }


def calculate_full_trade_pnl(
    buy_price: float,
    sell_price: float,
    quantity: int,
    holding_days: int,
    brokerage_per_order: float = DEFAULT_BROKERAGE,
    ltcg_exemption_used: float = 0.0,
) -> Dict:
    """
    Complete P&L calculation for a trade including all costs and taxes.
    Returns net real return after friction.
    """
    buy_value = buy_price * quantity
    sell_value = sell_price * quantity
    gross_pnl = (sell_price - buy_price) * quantity

    # Transaction costs
    costs = calculate_transaction_costs(buy_value, sell_value, brokerage_per_order)

    # Tax calculation (on gross P&L minus costs, but Indian tax is on gross P&L)
    tax = calculate_tax(gross_pnl, holding_days, ltcg_exemption_used)

    # Net P&L
    net_pnl = round(gross_pnl - costs["total_transaction_costs"] - tax["tax_amount"], 2)

    # Effective return percentage
    effective_return_pct = round((net_pnl / buy_value) * 100, 2) if buy_value > 0 else 0

    return {
        "buy_value": round(buy_value, 2),
        "sell_value": round(sell_value, 2),
        "gross_pnl": round(gross_pnl, 2),
        **costs,
        "tax_type": tax["tax_type"],
        "taxable_gain": tax["taxable_gain"],
        "tax_amount": tax["tax_amount"],
        "exemption_used": tax["exemption_used"],
        "net_pnl": net_pnl,
        "effective_return_pct": effective_return_pct,
    }


def estimate_position_costs(
    entry_price: float,
    target_price: float,
    stop_loss_price: float,
    quantity: int,
    brokerage_per_order: float = DEFAULT_BROKERAGE,
) -> Dict:
    """
    Estimate costs for a position at both target and stop scenarios.
    Useful for the position sizing calculator.
    """
    buy_value = entry_price * quantity

    # At target
    target_sell_value = target_price * quantity
    target_costs = calculate_transaction_costs(buy_value, target_sell_value, brokerage_per_order)
    target_gross_pnl = (target_price - entry_price) * quantity
    target_net_pnl = round(target_gross_pnl - target_costs["total_transaction_costs"], 2)

    # At stop loss
    stop_sell_value = stop_loss_price * quantity
    stop_costs = calculate_transaction_costs(buy_value, stop_sell_value, brokerage_per_order)
    stop_gross_pnl = (stop_loss_price - entry_price) * quantity
    stop_net_pnl = round(stop_gross_pnl - stop_costs["total_transaction_costs"], 2)

    return {
        "at_target": {
            "gross_pnl": round(target_gross_pnl, 2),
            "total_costs": target_costs["total_transaction_costs"],
            "net_pnl": target_net_pnl,
            "cost_breakdown": target_costs,
        },
        "at_stop": {
            "gross_pnl": round(stop_gross_pnl, 2),
            "total_costs": stop_costs["total_transaction_costs"],
            "net_pnl": stop_net_pnl,
            "cost_breakdown": stop_costs,
        },
    }
