"""
FastAPI Application Entry Point.
Personal Finance & Swing Trading Platform for Indian Equity Markets.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, SessionLocal
from app.seed import seed_all
from app.services.load_stocks import load_stocks_from_excel
from app.services.listing_tracker import sync_newly_listed_stocks
from app.routes import dashboard, screener, portfolio, calculator, journal, mid_small_scanner, penny_scanner, stocks, new_listings, paper_trading


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup: Initialize DB and seed demo data
    print("🚀 Starting TradeLab — Personal Finance & Swing Trading Platform")
    init_db()

    db = SessionLocal()
    try:
        load_stocks_from_excel(db)
        sync_newly_listed_stocks(db)
        seed_all(db)
        paper_trading.get_or_create_paper_account(db)
    finally:
        db.close()



    print("✅ Application ready at http://localhost:8000")
    print("📚 API Docs at http://localhost:8000/docs")

    yield

    # Shutdown
    print("🛑 Shutting down TradeLab...")


app = FastAPI(
    title="TradeLab — Personal Finance & Swing Trading Platform",
    description=(
        "Production-grade personal finance and automated swing-trading "
        "platform for the Indian equity market (NSE/BSE). Features EOD "
        "data ingestion, quantitative screening (VCP, accumulation, "
        "EMA pullback), ATR-based position sizing, and Indian tax "
        "calculations (STCG/LTCG)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(dashboard.router)
app.include_router(screener.router)
app.include_router(mid_small_scanner.router)
app.include_router(penny_scanner.router)
app.include_router(portfolio.router)
app.include_router(calculator.router)
app.include_router(journal.router)
app.include_router(stocks.router)
app.include_router(new_listings.router)
app.include_router(paper_trading.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TradeLab", "version": "1.0.0"}


@app.get("/api/symbols")
def get_symbols():
    """Get list of all available stock symbols."""
    from app.database import SessionLocal
    from app.services.ingestion import get_all_symbols

    db = SessionLocal()
    try:
        symbols = get_all_symbols(db)
        return {"symbols": sorted(symbols), "count": len(symbols)}
    finally:
        db.close()
