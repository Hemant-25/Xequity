"""
Analysis Router — End-of-Day (EOD) Trade Recommendations + News Feed
=====================================================================

Endpoints:
  POST /api/eod-analysis   — EOD buy/sell/hold for a list of NSE symbols
  GET  /api/news           — Latest Indian market headlines (RSS aggregated)
  GET  /api/news/macro     — Macroeconomic / policy news
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException

from models.schemas import EODAnalysisRequest, EODAnalysisResult
from services.market_data import (
    fetch_historical_data,
    fetch_fundamental_data,
    fetch_sector_performance,
)
from services.technicals import compute_technicals
from services.news_fetcher import (
    fetch_market_news,
    fetch_macro_news,
    fetch_all_news_for_symbols,
    format_news_for_prompt,
)
from services.claude_analyzer import analyze_eod_stocks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analysis"])


# --------------------------------------------------------------------------- #
# POST /api/eod-analysis
# --------------------------------------------------------------------------- #
@router.post("/eod-analysis", response_model=EODAnalysisResult)
async def eod_analysis(request: EODAnalysisRequest):
    """
    End-of-Day analysis for a watchlist of NSE symbols.

    Steps:
    1. Fetch historical OHLCV + compute full technical suite (MACD, ADX, ATR, OBV, Volume)
    2. Fetch fundamental data
    3. Fetch latest financial news (market + macro + per-stock) if requested
    4. Run Claude EOD analysis with entry/exit/stop-loss/R:R recommendations
    5. Return structured EODAnalysisResult
    """
    symbols = [s.strip().upper() for s in request.symbols]

    # ---- Step 1 & 2: Enrich each symbol ----
    stocks: list[dict] = []
    errors: list[dict] = []

    for symbol in symbols:
        try:
            logger.info(f"EOD: processing {symbol}...")
            df = fetch_historical_data(symbol)
            technical = compute_technicals(df)
            fundamental = fetch_fundamental_data(symbol)
            stocks.append(
                {
                    "symbol": symbol,
                    "technical": technical,
                    "fundamental": fundamental,
                }
            )
            await asyncio.sleep(0.3)  # polite rate-limiting

        except Exception as e:
            logger.error(f"EOD: failed to process {symbol}: {e}")
            errors.append({"symbol": symbol, "error": str(e)})

    if not stocks:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch data for any symbol. Errors: {errors}",
        )

    if errors:
        logger.warning(f"EOD: partial failures — {errors}")

    # ---- Step 3: Sector performance ----
    sector_perf: dict = {}
    try:
        sector_perf = fetch_sector_performance()
    except Exception as e:
        logger.warning(f"EOD: sector performance unavailable: {e}")

    # ---- Step 4: News aggregation ----
    news_block = ""
    if request.include_news:
        try:
            processed_symbols = [s["symbol"] for s in stocks]
            market_news, macro_news, stock_news_map = fetch_all_news_for_symbols(processed_symbols)
            news_block = format_news_for_prompt(market_news, macro_news, stock_news_map)
            logger.info(
                f"EOD: fetched {len(market_news)} market + {len(macro_news)} macro news items"
            )
        except Exception as e:
            logger.warning(f"EOD: news fetch failed (continuing without): {e}")

    # ---- Step 5: Claude EOD analysis ----
    try:
        result = await analyze_eod_stocks(
            stocks=stocks,
            trading_style=request.trading_style.value,
            news_block=news_block,
            additional_context=request.additional_context,
            sector_performance=sector_perf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"EOD: Claude analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

    return result


# --------------------------------------------------------------------------- #
# GET /api/news
# --------------------------------------------------------------------------- #
@router.get("/news")
async def get_market_news():
    """
    Latest Indian market headlines aggregated from ET, Moneycontrol,
    Business Standard, and LiveMint RSS feeds (cached 30 min).
    """
    try:
        news = fetch_market_news()
        return {"count": len(news), "news": news}
    except Exception as e:
        logger.error(f"Failed to fetch market news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- #
# GET /api/news/macro
# --------------------------------------------------------------------------- #
@router.get("/news/macro")
async def get_macro_news():
    """
    Macroeconomic & policy news — RBI, Budget, SEBI, GDP releases (cached 30 min).
    """
    try:
        news = fetch_macro_news()
        return {"count": len(news), "news": news}
    except Exception as e:
        logger.error(f"Failed to fetch macro news: {e}")
        raise HTTPException(status_code=500, detail=str(e))
