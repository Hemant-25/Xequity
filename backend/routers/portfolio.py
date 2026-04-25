import asyncio
import logging
from fastapi import APIRouter, HTTPException
from models.schemas import (
    PortfolioInput,
    AnalysisResult,
    EnrichedHolding,
)
from services.market_data import (
    fetch_historical_data,
    fetch_fundamental_data,
    fetch_sector_performance,
)
from services.technicals import compute_technicals
from services.claude_analyzer import analyze_portfolio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["portfolio"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(portfolio: PortfolioInput):
    """
    Main endpoint: accepts portfolio holdings, fetches live data,
    computes technicals, and runs Claude AI analysis.
    """
    enriched: list[EnrichedHolding] = []
    errors: list[dict] = []

    # Fetch data for each holding
    for holding in portfolio.holdings:
        try:
            logger.info(f"Processing {holding.symbol}...")

            # Fetch historical OHLCV
            df = fetch_historical_data(holding.symbol)

            # Compute technical indicators
            technical = compute_technicals(df)

            # Fetch fundamental data
            fundamental = fetch_fundamental_data(holding.symbol)

            # Calculate P&L
            pnl_pct = None
            if technical.current_price and holding.avg_buy_price > 0:
                pnl_pct = round(
                    (technical.current_price - holding.avg_buy_price)
                    / holding.avg_buy_price
                    * 100,
                    2,
                )

            enriched.append(
                EnrichedHolding(
                    symbol=holding.symbol.upper(),
                    avg_buy_price=holding.avg_buy_price,
                    allocation_pct=holding.allocation_pct,
                    technical=technical,
                    fundamental=fundamental,
                    pnl_pct=pnl_pct,
                )
            )

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.3)

        except Exception as e:
            logger.error(f"Failed to process {holding.symbol}: {e}")
            errors.append({"symbol": holding.symbol, "error": str(e)})

    if not enriched:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch data for any stock. Errors: {errors}",
        )

    if errors:
        logger.warning(f"Partial failures: {errors}")

    # Fetch sector performance for context
    sector_perf = {}
    try:
        sector_perf = fetch_sector_performance()
    except Exception as e:
        logger.warning(f"Could not fetch sector performance: {e}")

    # Run Claude analysis
    try:
        result = await analyze_portfolio(
            holdings=enriched,
            trading_style=portfolio.trading_style.value,
            additional_context=portfolio.additional_context,
            sector_performance=sector_perf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(e)}",
        )

    return result
