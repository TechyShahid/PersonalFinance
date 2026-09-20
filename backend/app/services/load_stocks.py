"""
Service to load listed stocks and market capitalization classification
from Excel file (backend/data/stocks.xlsx) into the SQLite 'stocks' table.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import engine, SessionLocal, Base, DATA_DIR
from app.models import Stock

logger = logging.getLogger(__name__)


def clean_val(val: Any) -> Optional[str]:
    """Clean string values, returning None for empty/dash/nan values."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in {"", "-", "nan", "None", "NaN"}:
        return None
    return s


def clean_float(val: Any) -> Optional[float]:
    """Safely convert value to float, returning None for invalid/missing values."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    if s in {"", "-", "nan", "None", "NaN"}:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def load_stocks_from_excel(db: Session, excel_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Parse stocks.xlsx and insert all records into the 'stocks' table.
    
    Args:
        db: SQLAlchemy session
        excel_path: Optional custom path to Excel file. Defaults to backend/data/stocks.xlsx.
        force_reload: If True, clears existing records and reloads.
        
    Returns:
        Dict with summary counts and category breakdown.
    """
    if not excel_path:
        excel_path = os.path.join(DATA_DIR, "stocks.xlsx")

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found at: {excel_path}")

    # Ensure table exists
    Base.metadata.create_all(bind=engine)

    existing_count = db.query(Stock).count()
    if existing_count > 0 and not force_reload:
        category_counts = {}
        for cat, cnt in db.query(Stock.category, func.count(Stock.id)).group_by(Stock.category).all():
            category_counts[cat or "Uncategorized"] = cnt
        return {
            "status": "already_loaded",
            "total_count": existing_count,
            "category_counts": category_counts,
            "message": f"Table 'stocks' already contains {existing_count} records. Use force_reload=True to overwrite."
        }

    if force_reload and existing_count > 0:
        db.query(Stock).delete()
        db.commit()

    print(f"Reading Excel file: {excel_path}...")
    df = pd.read_excel(excel_path, sheet_name="FINAL", skiprows=1)

    records = []
    category_counter = {}

    for _, row in df.iterrows():
        sr_no = int(row["Sr. No."]) if pd.notna(row["Sr. No."]) else None
        company_name = str(row["Company name"]).strip() if pd.notna(row["Company name"]) else ""
        isin = str(row["ISIN"]).strip() if pd.notna(row["ISIN"]) else ""
        bse_sym = clean_val(row.get("BSE Symbol"))
        bse_mcap = clean_float(row.get("BSE 6 month Avg Total Market Cap in (Rs. Crs.)"))
        nse_sym = clean_val(row.get("NSE Symbol"))
        nse_mcap = clean_float(row.get("NSE 6 month Avg Total Market Cap (Rs. Crs.)"))
        msei_sym = clean_val(row.get("MSEI Symbol"))
        msei_mcap = clean_float(row.get("MSEI 6 month Avg Total Market Cap in (Rs Crs.)"))
        avg_mcap = clean_float(row.get("Average of All Exchanges (Rs. Cr.)"))
        cat = clean_val(row.get("Categorization as per SEBI Circular dated Oct 6, 2017"))

        rec = {
            "sr_no": sr_no,
            "company_name": company_name,
            "isin": isin,
            "bse_symbol": bse_sym,
            "bse_mcap_cr": bse_mcap,
            "nse_symbol": nse_sym,
            "nse_mcap_cr": nse_mcap,
            "msei_symbol": msei_sym,
            "msei_mcap_cr": msei_mcap,
            "avg_mcap_cr": avg_mcap,
            "category": cat,
        }
        records.append(rec)
        category_counter[cat or "Uncategorized"] = category_counter.get(cat or "Uncategorized", 0) + 1

    print(f"Inserting {len(records)} stocks into database...")
    db.bulk_insert_mappings(Stock, records)
    db.commit()

    total = db.query(Stock).count()
    print(f"Successfully loaded {total} stocks.")

    return {
        "status": "success",
        "total_count": total,
        "category_counts": category_counter,
        "message": f"Successfully loaded {total} stocks from {excel_path}"
    }


if __name__ == "__main__":
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        result = load_stocks_from_excel(db, force_reload=force)
        print("Result:", result)
    finally:
        db.close()
