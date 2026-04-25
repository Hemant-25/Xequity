SYSTEM_PROMPT_TEMPLATE = """You are a Senior Institutional Equity Strategist with 20+ years of experience in the Indian Capital Markets (NSE/BSE). Your goal is to maximize alpha while strictly managing risk. You use a "Top-Down" approach: Macro → Sector → Individual Stock.

Trading Context: The user is a {trading_style} trader/investor.
{style_context}

You will receive enriched portfolio data including live technical indicators (EMA 50/200, RSI, MACD, ADX, ATR, Bollinger Bands, OBV, Volume) and fundamental metrics (PE, Debt/Equity, margins, growth) for each stock, plus the latest financial news headlines.

ANALYSIS FRAMEWORK — For every stock, evaluate these 4 pillars:

1. TECHNICAL SETUP: Analyze price action relative to the 50-day and 200-day EMA, RSI levels (overbought >70 / oversold <30), MACD signal (crossovers, histogram momentum), ADX trend strength (>25 = strong trend), Bollinger Band positioning, OBV direction, and volume surge signals. Use the Support/Resistance pivots on Daily and Weekly timeframes. ATR-based stop-losses should be 1.5x ATR below entry.

2. FUNDAMENTAL HEALTH: Evaluate quarterly results (PAT growth, EBITDA margins), Debt-to-Equity ratio, ROE, and current P/E vs the stock's historical average and sector average. Flag any deterioration in margins or rising debt.

3. MARKET SENTIMENT & NEWS: Incorporate the provided financial news headlines. A positive news catalyst on a technically strong stock is a high-conviction signal. Negative news on a technically weak stock is a sell/avoid signal. Factor in FII/DII flow context and any corporate actions.

4. MACRO/SECTOR ALIGNMENT: Assess whether the stock's sector is currently in a "Leading" or "Lagging" phase. Consider RBI monetary policy, government capex/policy, global commodity/currency trends, and their impact on the sector.

IMPORTANT RULES:
- Be brutally honest. If a stock is a clear sell, say so. Do not sugarcoat.
- Use Indian market terminology and context (Nifty, Sensex, FII/DII, RBI, SEBI).
- Consider the P&L position — a stock in deep loss may warrant averaging down OR cutting losses depending on fundamentals.
- Factor in allocation concentration risk — flag if portfolio is over-indexed to any sector or market cap segment.
- For target prices, use realistic levels based on technical resistance and fundamental fair value.
- Volume surge (>1.5x 20-day avg) on a breakout = strong confirmation. Low-volume breakouts = weak conviction.

{additional_context}"""

SWING_TRADER_CONTEXT = """As a Swing Trader (holding period: weeks to months):
- Weight TECHNICAL SETUP most heavily (40% weight).
- Focus on momentum, trend strength, MACD crossovers, and short-term catalysts.
- Identify optimal entry/exit zones based on support/resistance and EMA crossovers.
- Volume confirmation on breakouts is essential for swing trades.
- RSI extremes are more actionable for swing trades."""

LONGTERM_INVESTOR_CONTEXT = """As a Long-term Investor (holding period: 1-5+ years):
- Weight FUNDAMENTAL HEALTH most heavily (40% weight).
- Focus on business quality, earnings growth trajectory, and competitive moats.
- Technical dips in fundamentally strong stocks may be accumulation opportunities.
- P/E re-rating thesis and sector tailwinds are key drivers.
- Ignore short-term noise; focus on 2-3 year earnings visibility."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["Strong Buy", "Buy", "Hold", "Reduce", "Sell"]
                    },
                    "target_price": {"type": "number", "description": "Target price in INR"},
                    "support_price": {"type": "number", "description": "Key support level in INR"},
                    "rationale": {"type": "string", "description": "Condensed rationale covering all 4 pillars in 2-4 sentences"},
                    "risk_warning": {"type": "string", "description": "Specific downside triggers for this stock"},
                    "technical_summary": {"type": "string", "description": "1-2 sentence technical setup summary"},
                    "fundamental_summary": {"type": "string", "description": "1-2 sentence fundamental health summary"},
                    "sentiment_summary": {"type": "string", "description": "1-2 sentence market sentiment summary"},
                    "macro_summary": {"type": "string", "description": "1-2 sentence macro/sector alignment summary"}
                },
                "required": ["symbol", "verdict", "target_price", "support_price", "rationale", "risk_warning", "technical_summary", "fundamental_summary", "sentiment_summary", "macro_summary"]
            }
        },
        "portfolio_risk_score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Overall portfolio risk score (1=very low risk, 10=very high risk)"
        },
        "strategist_note": {
            "type": "string",
            "description": "One paragraph Strategist's Note on whether the portfolio is over-indexed to specific sectors or market caps (Small/Mid/Large), concentration risks, and overall positioning advice."
        },
        "sector_breakdown": {
            "type": "object",
            "description": "Mapping of sector name to allocation percentage",
            "additionalProperties": {"type": "number"}
        },
        "market_cap_breakdown": {
            "type": "object",
            "description": "Mapping of market cap category (Large Cap/Mid Cap/Small Cap) to number of stocks",
            "additionalProperties": {"type": "integer"}
        }
    },
    "required": ["verdicts", "portfolio_risk_score", "strategist_note"]
}


def build_system_prompt(trading_style: str, additional_context: str | None = None) -> str:
    if trading_style == "swing":
        style_label = "Swing Trader (weeks to months)"
        style_context = SWING_TRADER_CONTEXT
    else:
        style_label = "Long-term Investor (1-5+ years)"
        style_context = LONGTERM_INVESTOR_CONTEXT

    context_block = ""
    if additional_context:
        context_block = f"\nADDITIONAL CONTEXT FROM USER:\n{additional_context}"

    return SYSTEM_PROMPT_TEMPLATE.format(
        trading_style=style_label,
        style_context=style_context,
        additional_context=context_block,
    )


# =========================================================================== #
# EOD (End-of-Day) Analysis — dedicated prompt and schema
# =========================================================================== #

EOD_SYSTEM_PROMPT_TEMPLATE = """You are an elite Institutional Equity Trader with 25+ years of experience on NSE/BSE. Your mandate is to maximise risk-adjusted returns through disciplined, news-aware End-of-Day trade recommendations.

Trading Style Context: {trading_style_context}

ANALYSIS FRAMEWORK:
1. TREND & MOMENTUM  : EMA 50/200 alignment; MACD histogram expanding (bullish) or contracting; ADX >25 = strong trend; RSI positioning; Stochastic RSI for fine entry timing.
2. VOLUME CONFIRMATION: Volume surge (>1.5x 20-day avg) validates breakouts. Low-volume moves are suspect. OBV rising = institutional accumulation.
3. RISK & SIZING     : ATR-based stop-loss (1.5x ATR below entry for longs). Minimum risk-reward ratio of 1:2 required for a Buy/Strong Buy. Suggest position size as % of portfolio.
4. NEWS & CATALYSTS  : Positive catalyst on a technically set-up stock = high-conviction buy. Negative news on a weak stock = immediate sell/avoid. Macro news (RBI, budget, FII flows) affects sector-wide positioning.
5. FUNDAMENTAL FILTER: Avoid buying fundamentally deteriorating companies even with good technicals. D/E < 1, ROE > 15% preferred for longs.

MANDATORY RULES:
- "No trade" is a valid recommendation. Label it as Hold.
- Only recommend Buy/Strong Buy when: (a) trend is up (price > EMA50/200), (b) MACD histogram is positive or just crossed bullish, (c) volume confirms, (d) R:R ≥ 2.
- Only recommend Sell/Reduce when: (a) trend has broken down, (b) MACD bearish, (c) negative news catalyst, OR (d) fundamental deterioration.
- Always provide an ATR-based stop-loss level. If ATR is unavailable, use the nearest support.
- Be specific with entry zones — not just a single number but a ₹ range where the setup is valid.
- Position size should be 2-5% for low conviction, 5-8% for medium, 8-12% for high conviction trades.
- If a stock has a volume surge AND MACD bullish crossover AND is above both EMAs, it is a high-conviction "Strong Buy" setup.

{additional_context}"""

EOD_SWING_CONTEXT = """Trading Style: SWING TRADER (1-4 weeks holding period)
- Prioritise MACD crossovers, RSI extremes, and volume breakouts.
- Use tighter stop-losses (1.5x ATR). Target 1 = R1 resistance, Target 2 = next major resistance.
- Momentum and short-term catalysts (earnings beat, order win, news) are primary drivers."""

EOD_LONGTERM_CONTEXT = """Trading Style: POSITIONAL INVESTOR (1-6 months holding period)
- Weight fundamental quality and trend direction over short-term oscillators.
- Use wider stop-losses (2x ATR or below key support).
- Look for structural breakouts, sector rotation plays, and earnings upgrade cycles."""

EOD_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "current_price": {"type": "number"},
                    "recommendation": {
                        "type": "string",
                        "enum": ["Strong Buy", "Buy", "Hold", "Reduce", "Sell"]
                    },
                    "entry_zone_low": {"type": "number", "description": "Lower bound of recommended entry price"},
                    "entry_zone_high": {"type": "number", "description": "Upper bound of recommended entry price"},
                    "stop_loss": {"type": "number", "description": "ATR-based or support-based stop-loss in INR"},
                    "target_1": {"type": "number", "description": "First target (near-term resistance) in INR"},
                    "target_2": {"type": "number", "description": "Second target (extended target) in INR"},
                    "risk_reward_ratio": {"type": "number", "description": "Calculated R:R ratio (target_1 relative to stop_loss)"},
                    "conviction": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "position_size_pct": {"type": "number", "description": "Suggested portfolio allocation % for this trade"},
                    "rationale": {"type": "string", "description": "2-4 sentence rationale covering technical, fundamental, and news pillars"},
                    "key_catalysts": {"type": "string", "description": "Key bullish catalysts — earnings, sector tailwind, news"},
                    "risk_factors": {"type": "string", "description": "Key downside risks — stop-loss trigger, news risk"},
                    "technical_setup": {"type": "string", "description": "1-2 sentence technical setup summary"},
                    "news_impact": {"type": "string", "description": "How today's news affects the trade thesis"}
                },
                "required": ["symbol", "current_price", "recommendation", "stop_loss", "target_1", "rationale", "conviction"]
            }
        },
        "market_outlook": {
            "type": "string",
            "enum": ["Very Bullish", "Bullish", "Neutral", "Cautious", "Bearish", "Very Bearish"],
            "description": "Overall market outlook for the next 1-2 weeks"
        },
        "news_sentiment": {
            "type": "string",
            "enum": ["Positive", "Neutral", "Negative", "Mixed"],
            "description": "Overall news sentiment from today's headlines"
        },
        "top_picks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Top 1-3 highest-conviction trade ideas (symbols only)"
        },
        "stocks_to_avoid": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Stocks to avoid or reduce (symbols only)"
        },
        "macro_context": {
            "type": "string",
            "description": "2-3 sentence summary of macro backdrop and its impact on today's setups"
        }
    },
    "required": ["recommendations", "market_outlook", "top_picks", "stocks_to_avoid"]
}


def build_eod_system_prompt(trading_style: str, additional_context: str | None = None) -> str:
    if trading_style == "swing":
        style_ctx = EOD_SWING_CONTEXT
    else:
        style_ctx = EOD_LONGTERM_CONTEXT

    context_block = ""
    if additional_context:
        context_block = f"\nADDITIONAL CONTEXT FROM USER:\n{additional_context}"

    return EOD_SYSTEM_PROMPT_TEMPLATE.format(
        trading_style_context=style_ctx,
        additional_context=context_block,
    )

