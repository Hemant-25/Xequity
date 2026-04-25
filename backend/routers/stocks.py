import logging
from fastapi import APIRouter, HTTPException
from services.market_data import fetch_stock_price, fetch_sector_performance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stocks"])


@router.get("/stock/{symbol}")
async def get_stock(symbol: str):
    """Fetch current price and basic info for a stock symbol (for validation/autocomplete)."""
    result = fetch_stock_price(symbol)
    if not result.get("valid"):
        raise HTTPException(
            status_code=404,
            detail=f"Stock '{symbol}' not found on NSE. Please check the symbol.",
        )
    return result


@router.get("/sectors")
async def get_sectors():
    """Get Nifty sector index performance (1M and 3M returns)."""
    try:
        data = fetch_sector_performance()
        return {"sectors": data}
    except Exception as e:
        logger.error(f"Failed to fetch sector data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
