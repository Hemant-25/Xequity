from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TradingStyle(str, Enum):
    SWING = "swing"
    LONGTERM = "longterm"


class StockHolding(BaseModel):
    symbol: str = Field(..., description="NSE stock symbol (e.g., RELIANCE, TCS)")
    avg_buy_price: float = Field(..., gt=0, description="Average buy price in INR")
    allocation_pct: float = Field(..., gt=0, le=100, description="Portfolio allocation percentage")


class PortfolioInput(BaseModel):
    holdings: list[StockHolding] = Field(..., min_length=1, max_length=20)
    trading_style: TradingStyle = TradingStyle.LONGTERM
    additional_context: Optional[str] = Field(None, max_length=2000, description="Optional news, events, or market context")


class TechnicalData(BaseModel):
    current_price: float
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    rsi_14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    ema_signal: Optional[str] = None  # "Bullish", "Bearish", "Neutral"
    rsi_signal: Optional[str] = None  # "Overbought", "Oversold", "Neutral"
    price_vs_ema200: Optional[str] = None  # "Above", "Below"
    weekly_change_pct: Optional[float] = None
    monthly_change_pct: Optional[float] = None

    # --- Advanced indicators ---
    # MACD (12, 26, 9)
    macd: Optional[float] = None
    macd_signal_line: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_signal: Optional[str] = None  # "Bullish Crossover", "Bearish Crossover", "Bullish Momentum", "Bearish Momentum", "Neutral"

    # ADX (14) — trend strength
    adx: Optional[float] = None
    adx_signal: Optional[str] = None  # "Strong Trend (>25)", "Moderate Trend (20-25)", "Weak/Ranging (<20)"

    # ATR (14) — volatility / stop-loss sizing
    atr: Optional[float] = None

    # Stochastic RSI
    stoch_rsi_k: Optional[float] = None

    # On-Balance Volume direction
    obv_signal: Optional[str] = None  # "Bullish", "Bearish", "Neutral"

    # Volume analysis
    volume_ratio: Optional[float] = None   # today_volume / 20-day-avg-volume
    volume_surge: Optional[bool] = None    # True when volume_ratio > 1.5


class FundamentalData(BaseModel):
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    dividend_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None
    ebitda_margins: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None


class EnrichedHolding(BaseModel):
    symbol: str
    avg_buy_price: float
    allocation_pct: float
    technical: TechnicalData
    fundamental: FundamentalData
    pnl_pct: Optional[float] = None  # Current P&L %


class Verdict(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    REDUCE = "Reduce"
    SELL = "Sell"


class StockVerdict(BaseModel):
    symbol: str
    verdict: Verdict
    target_price: Optional[float] = None
    support_price: Optional[float] = None
    rationale: str = Field(..., description="Condensed rationale covering the 4 pillars")
    risk_warning: str = Field(..., description="Specific downside triggers")
    technical_summary: Optional[str] = None
    fundamental_summary: Optional[str] = None
    sentiment_summary: Optional[str] = None
    macro_summary: Optional[str] = None


class AnalysisResult(BaseModel):
    verdicts: list[StockVerdict]
    portfolio_risk_score: int = Field(..., ge=1, le=10)
    strategist_note: str
    sector_breakdown: Optional[dict[str, float]] = None
    market_cap_breakdown: Optional[dict[str, int]] = None


# --------------------------------------------------------------------------- #
# End-of-Day (EOD) Analysis schemas
# --------------------------------------------------------------------------- #

class EODAnalysisRequest(BaseModel):
    symbols: list[str] = Field(
        ..., min_length=1, max_length=50,
        description="NSE symbols to analyse (e.g. ['RELIANCE', 'TCS'])"
    )
    trading_style: TradingStyle = TradingStyle.SWING
    additional_context: Optional[str] = Field(None, max_length=2000)
    include_news: bool = Field(True, description="Auto-fetch financial news and include in analysis")


class EODStockRecommendation(BaseModel):
    symbol: str
    current_price: float
    recommendation: Verdict
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    conviction: Optional[str] = None          # "High", "Medium", "Low"
    position_size_pct: Optional[float] = None  # Suggested % of portfolio
    rationale: str
    key_catalysts: Optional[str] = None
    risk_factors: Optional[str] = None
    technical_setup: Optional[str] = None
    news_impact: Optional[str] = None


class EODAnalysisResult(BaseModel):
    analysis_date: str
    market_outlook: str
    news_sentiment: Optional[str] = None       # "Positive", "Neutral", "Negative", "Mixed"
    macro_context: Optional[str] = None
    top_picks: list[str] = Field(default_factory=list)
    stocks_to_avoid: list[str] = Field(default_factory=list)
    recommendations: list[EODStockRecommendation]
