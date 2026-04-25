import yfinance as yf
import pandas as pd
from models.schemas import FundamentalData, TechnicalData
from functools import lru_cache
import time
import logging

logger = logging.getLogger(__name__)

# Cache stock objects to avoid redundant API calls within same session
_stock_cache: dict[str, tuple[float, any]] = {}
CACHE_TTL = 900  # 15 minutes


def _get_ticker(symbol: str) -> yf.Ticker:
    nse_symbol = f"{symbol.upper()}.NS"
    now = time.time()

    if nse_symbol in _stock_cache:
        cached_time, ticker = _stock_cache[nse_symbol]
        if now - cached_time < CACHE_TTL:
            return ticker

    ticker = yf.Ticker(nse_symbol)
    _stock_cache[nse_symbol] = (now, ticker)
    return ticker


def fetch_stock_price(symbol: str) -> dict:
    """Fetch current price and basic info for validation/autocomplete."""
    try:
        ticker = _get_ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol.upper(),
            "name": info.get("shortName") or info.get("longName", symbol),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "valid": True,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
        return {"symbol": symbol.upper(), "valid": False, "error": str(e)}


def fetch_historical_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch daily OHLCV data for technical analysis."""
    ticker = _get_ticker(symbol)
    df = ticker.history(period=period)
    if df.empty:
        raise ValueError(f"No historical data available for {symbol}.NS")
    return df


def fetch_fundamental_data(symbol: str) -> FundamentalData:
    """Extract fundamental metrics from yfinance info dict."""
    ticker = _get_ticker(symbol)
    info = ticker.info

    # Try to compute profit/revenue growth from quarterly financials
    revenue_growth = None
    profit_growth = None
    ebitda_margins = None

    try:
        quarterly = ticker.quarterly_income_stmt
        if quarterly is not None and not quarterly.empty and quarterly.shape[1] >= 2:
            # Latest quarter vs same quarter last year (if 4+ quarters available)
            if quarterly.shape[1] >= 4:
                latest_rev = quarterly.iloc[0, 0] if "Total Revenue" in quarterly.index else None
                yoy_rev = quarterly.iloc[0, 3] if "Total Revenue" in quarterly.index else None

                if latest_rev and yoy_rev and yoy_rev != 0:
                    rev_row = quarterly.loc["Total Revenue"] if "Total Revenue" in quarterly.index else None
                    if rev_row is not None:
                        revenue_growth = float((rev_row.iloc[0] - rev_row.iloc[3]) / abs(rev_row.iloc[3]) * 100)

                if "Net Income" in quarterly.index:
                    ni_row = quarterly.loc["Net Income"]
                    if ni_row.iloc[3] != 0:
                        profit_growth = float((ni_row.iloc[0] - ni_row.iloc[3]) / abs(ni_row.iloc[3]) * 100)

            if "EBITDA" in quarterly.index and "Total Revenue" in quarterly.index:
                ebitda_val = quarterly.loc["EBITDA"].iloc[0]
                rev_val = quarterly.loc["Total Revenue"].iloc[0]
                if rev_val and rev_val != 0:
                    ebitda_margins = float(ebitda_val / rev_val * 100)
    except Exception as e:
        logger.debug(f"Could not compute growth metrics for {symbol}: {e}")

    return FundamentalData(
        market_cap=info.get("marketCap"),
        pe_ratio=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        pb_ratio=info.get("priceToBook"),
        debt_to_equity=info.get("debtToEquity"),
        roe=info.get("returnOnEquity"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        dividend_yield=info.get("dividendYield"),
        revenue_growth=revenue_growth,
        profit_growth=profit_growth,
        ebitda_margins=ebitda_margins,
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
    )


# Major Nifty sector indices for sector performance comparison
SECTOR_INDICES = {
    "Nifty 50": "^NSEI",
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Auto": "NIFTY_AUTO.NS",
    "Nifty FMCG": "NIFTY_FMCG.NS",
    "Nifty Metal": "NIFTY_METAL.NS",
    "Nifty Realty": "NIFTY_REALTY.NS",
    "Nifty Energy": "NIFTY_ENERGY.NS",
    "Nifty Infra": "NIFTY_INFRA.NS",
}


def fetch_sector_performance() -> dict[str, dict]:
    """Fetch 1-month and 3-month returns for major Nifty sector indices."""
    results = {}
    for name, ticker_symbol in SECTOR_INDICES.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="3mo")
            if hist.empty or len(hist) < 5:
                continue

            current = hist["Close"].iloc[-1]
            one_month_ago = hist["Close"].iloc[-min(22, len(hist))]
            three_months_ago = hist["Close"].iloc[0]

            results[name] = {
                "1m_return": round((current - one_month_ago) / one_month_ago * 100, 2),
                "3m_return": round((current - three_months_ago) / three_months_ago * 100, 2),
            }
        except Exception as e:
            logger.debug(f"Could not fetch sector index {name}: {e}")
            continue

    return results
