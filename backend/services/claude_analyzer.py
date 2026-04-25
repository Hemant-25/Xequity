import json
import os
import logging
from datetime import date
from anthropic import Anthropic
from models.schemas import (
    AnalysisResult,
    EnrichedHolding,
    EODAnalysisResult,
    EODStockRecommendation,
    StockVerdict,
    TechnicalData,
    FundamentalData,
    Verdict,
)
from models.prompts import (
    build_system_prompt,
    build_eod_system_prompt,
    OUTPUT_SCHEMA,
    EOD_OUTPUT_SCHEMA,
)

logger = logging.getLogger(__name__)


def _get_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        raise ValueError(
            "ANTHROPIC_API_KEY not configured. "
            "Copy .env.example to .env and add your API key."
        )
    return Anthropic(api_key=api_key)


def _build_user_message(
    holdings: list[EnrichedHolding],
    sector_performance: dict | None = None,
) -> str:
    """Build the user message containing all enriched portfolio data."""
    lines = ["## PORTFOLIO DATA\n"]

    for h in holdings:
        t = h.technical
        f = h.fundamental
        pnl = h.pnl_pct

        lines.append(f"### {h.symbol}")
        lines.append(f"- Allocation: {h.allocation_pct}% | Avg Buy: ₹{h.avg_buy_price} | CMP: ₹{t.current_price} | P&L: {pnl:+.1f}%" if pnl is not None else f"- Allocation: {h.allocation_pct}% | Avg Buy: ₹{h.avg_buy_price} | CMP: ₹{t.current_price}")
        lines.append(f"- **Technical**: EMA50={t.ema_50}, EMA200={t.ema_200}, RSI14={t.rsi_14} ({t.rsi_signal}), EMA Signal={t.ema_signal}, Price vs 200EMA={t.price_vs_ema200}")
        lines.append(f"  BB Upper={t.bb_upper}, BB Lower={t.bb_lower}, Support=₹{t.support_level}, Resistance=₹{t.resistance_level}")
        lines.append(f"  Weekly Change={t.weekly_change_pct}%, Monthly Change={t.monthly_change_pct}%")
        lines.append(f"- **Fundamental**: Sector={f.sector}, Industry={f.industry}")
        lines.append(f"  PE={f.pe_ratio}, Forward PE={f.forward_pe}, PB={f.pb_ratio}, D/E={f.debt_to_equity}, ROE={f.roe}")
        lines.append(f"  Revenue Growth={f.revenue_growth}%, Profit Growth={f.profit_growth}%, EBITDA Margin={f.ebitda_margins}%")
        lines.append(f"  Market Cap=₹{_format_market_cap(f.market_cap)}, Div Yield={f.dividend_yield}")
        lines.append(f"  52W High=₹{f.fifty_two_week_high}, 52W Low=₹{f.fifty_two_week_low}")
        lines.append("")

    if sector_performance:
        lines.append("## SECTOR INDEX PERFORMANCE (Nifty Sector Indices)\n")
        for sector, perf in sector_performance.items():
            lines.append(f"- {sector}: 1M={perf.get('1m_return', 'N/A')}%, 3M={perf.get('3m_return', 'N/A')}%")
        lines.append("")

    lines.append("---")
    lines.append("Analyze each stock and provide Buy/Hold/Sell verdicts with the 4-pillar framework. Return the result as structured JSON.")

    return "\n".join(lines)


def _format_market_cap(cap: float | None) -> str:
    if cap is None:
        return "N/A"
    if cap >= 1e12:
        return f"{cap / 1e12:.1f}L Cr"
    if cap >= 1e9:
        return f"{cap / 1e7:.0f} Cr"
    if cap >= 1e7:
        return f"{cap / 1e7:.1f} Cr"
    return str(cap)


async def analyze_portfolio(
    holdings: list[EnrichedHolding],
    trading_style: str,
    additional_context: str | None = None,
    sector_performance: dict | None = None,
) -> AnalysisResult:
    """Send enriched portfolio data to Claude for structured analysis."""
    client = _get_client()

    system_prompt = build_system_prompt(trading_style, additional_context)
    user_message = _build_user_message(holdings, sector_performance)

    logger.info(f"Sending {len(holdings)} stocks to Claude for analysis...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text response and parse JSON
    response_text = message.content[0].text

    # Try to extract JSON from the response
    parsed = _extract_json(response_text)

    return _parse_analysis_result(parsed)


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude's response, handling markdown code blocks."""
    # Try direct JSON parse first
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from markdown code block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        candidate = text[start:end].strip()
        if candidate.startswith("{"):
            return json.loads(candidate)

    # Last resort: find first { and last }
    first_brace = text.index("{")
    last_brace = text.rindex("}")
    return json.loads(text[first_brace : last_brace + 1])


def _parse_analysis_result(data: dict) -> AnalysisResult:
    """Parse Claude's JSON response into AnalysisResult model."""
    verdicts = []
    for v in data.get("verdicts", []):
        verdict_str = v.get("verdict", "Hold")
        # Normalize verdict to match enum
        try:
            verdict_enum = Verdict(verdict_str)
        except ValueError:
            verdict_map = {
                "strong buy": Verdict.STRONG_BUY,
                "buy": Verdict.BUY,
                "hold": Verdict.HOLD,
                "reduce": Verdict.REDUCE,
                "sell": Verdict.SELL,
            }
            verdict_enum = verdict_map.get(verdict_str.lower(), Verdict.HOLD)

        verdicts.append(
            StockVerdict(
                symbol=v.get("symbol", ""),
                verdict=verdict_enum,
                target_price=v.get("target_price"),
                support_price=v.get("support_price"),
                rationale=v.get("rationale", ""),
                risk_warning=v.get("risk_warning", ""),
                technical_summary=v.get("technical_summary"),
                fundamental_summary=v.get("fundamental_summary"),
                sentiment_summary=v.get("sentiment_summary"),
                macro_summary=v.get("macro_summary"),
            )
        )

    risk_score = data.get("portfolio_risk_score", 5)
    risk_score = max(1, min(10, int(risk_score)))

    return AnalysisResult(
        verdicts=verdicts,
        portfolio_risk_score=risk_score,
        strategist_note=data.get("strategist_note", ""),
        sector_breakdown=data.get("sector_breakdown"),
        market_cap_breakdown=data.get("market_cap_breakdown"),
    )


# =========================================================================== #
# EOD Analysis
# =========================================================================== #

def _build_eod_user_message(
    stocks: list[dict],  # each dict: {symbol, technical, fundamental}
    news_block: str,
    sector_performance: dict | None = None,
) -> str:
    """
    Build the EOD user message with full technical indicator suite,
    fundamentals, and aggregated news context.
    """
    lines: list[str] = [
        f"## EOD MARKET DATA — {date.today().strftime('%d %b %Y')}\n"
    ]

    # News block (market + macro + stock-specific)
    if news_block:
        lines.append(news_block)
        lines.append("")

    # Sector performance context
    if sector_performance:
        lines.append("## NIFTY SECTOR INDEX PERFORMANCE\n")
        for sector_name, perf in sector_performance.items():
            lines.append(
                f"- {sector_name}: 1M={perf.get('1m_return', 'N/A')}%, 3M={perf.get('3m_return', 'N/A')}%"
            )
        lines.append("")

    lines.append("## STOCK DATA\n")

    for s in stocks:
        sym: str = s["symbol"]
        t: TechnicalData = s["technical"]
        f: FundamentalData = s["fundamental"]

        lines.append(f"### {sym}  |  CMP: ₹{t.current_price}")

        # ---- Trend & EMA ----
        lines.append(
            f"- **EMA Signal**: {t.ema_signal} | EMA50={t.ema_50} | EMA200={t.ema_200} | vs 200EMA: {t.price_vs_ema200}"
        )

        # ---- Momentum ----
        lines.append(
            f"- **RSI(14)**: {t.rsi_14} ({t.rsi_signal}) | StochRSI-K: {t.stoch_rsi_k}"
        )
        lines.append(
            f"- **MACD**: Line={t.macd} | Signal={t.macd_signal_line} | Histogram={t.macd_histogram} → {t.macd_signal}"
        )

        # ---- Trend Strength & Volatility ----
        lines.append(
            f"- **ADX(14)**: {t.adx} ({t.adx_signal}) | ATR(14): ₹{t.atr}"
        )
        atr_stop = round(t.current_price - 1.5 * t.atr, 2) if t.atr else "N/A"
        lines.append(f"  → ATR-based stop (1.5x): ₹{atr_stop}")

        # ---- Bollinger & Pivot ----
        lines.append(
            f"- **Bollinger Bands**: Upper=₹{t.bb_upper} | Lower=₹{t.bb_lower}"
        )
        lines.append(
            f"- **Pivot S/R**: Support=₹{t.support_level} | Resistance=₹{t.resistance_level}"
        )

        # ---- Volume ----
        vol_tag = "🔥 VOLUME SURGE" if t.volume_surge else ""
        lines.append(
            f"- **Volume**: Ratio={t.volume_ratio}x 20-day avg | OBV Direction: {t.obv_signal} {vol_tag}"
        )

        # ---- Returns ----
        lines.append(
            f"- **Returns**: Weekly={t.weekly_change_pct}% | Monthly={t.monthly_change_pct}%"
        )
        lines.append(
            f"- **52W**: High=₹{f.fifty_two_week_high} | Low=₹{f.fifty_two_week_low}"
        )

        # ---- Fundamentals ----
        lines.append(
            f"- **Sector**: {f.sector} | {f.industry}"
        )
        lines.append(
            f"- **Fundamentals**: PE={f.pe_ratio} | Fwd PE={f.forward_pe} | PB={f.pb_ratio} | D/E={f.debt_to_equity} | ROE={f.roe}"
        )
        lines.append(
            f"  Revenue Growth={f.revenue_growth}% | Profit Growth={f.profit_growth}% | EBITDA Margin={f.ebitda_margins}%"
        )
        lines.append(
            f"  Market Cap=₹{_format_market_cap(f.market_cap)} | Div Yield={f.dividend_yield}"
        )
        lines.append("")

    lines.append("---")
    lines.append(
        "Generate EOD buy/sell/hold recommendations with precise entry zones, stop-losses, "
        "targets, and R:R ratios. Incorporate news impact. Return structured JSON only."
    )

    return "\n".join(lines)


def _parse_eod_result(data: dict) -> EODAnalysisResult:
    """Parse Claude's EOD JSON response into EODAnalysisResult."""
    verdict_map = {
        "strong buy": Verdict.STRONG_BUY,
        "buy": Verdict.BUY,
        "hold": Verdict.HOLD,
        "reduce": Verdict.REDUCE,
        "sell": Verdict.SELL,
    }

    recommendations: list[EODStockRecommendation] = []
    for r in data.get("recommendations", []):
        rec_str = r.get("recommendation", "Hold")
        try:
            rec_enum = Verdict(rec_str)
        except ValueError:
            rec_enum = verdict_map.get(rec_str.lower(), Verdict.HOLD)

        recommendations.append(
            EODStockRecommendation(
                symbol=r.get("symbol", ""),
                current_price=float(r.get("current_price", 0)),
                recommendation=rec_enum,
                entry_zone_low=r.get("entry_zone_low"),
                entry_zone_high=r.get("entry_zone_high"),
                stop_loss=r.get("stop_loss"),
                target_1=r.get("target_1"),
                target_2=r.get("target_2"),
                risk_reward_ratio=r.get("risk_reward_ratio"),
                conviction=r.get("conviction"),
                position_size_pct=r.get("position_size_pct"),
                rationale=r.get("rationale", ""),
                key_catalysts=r.get("key_catalysts"),
                risk_factors=r.get("risk_factors"),
                technical_setup=r.get("technical_setup"),
                news_impact=r.get("news_impact"),
            )
        )

    return EODAnalysisResult(
        analysis_date=date.today().isoformat(),
        market_outlook=data.get("market_outlook", "Neutral"),
        news_sentiment=data.get("news_sentiment"),
        macro_context=data.get("macro_context"),
        top_picks=data.get("top_picks", []),
        stocks_to_avoid=data.get("stocks_to_avoid", []),
        recommendations=recommendations,
    )


async def analyze_eod_stocks(
    stocks: list[dict],  # [{symbol, technical, fundamental}]
    trading_style: str,
    news_block: str = "",
    additional_context: str | None = None,
    sector_performance: dict | None = None,
) -> EODAnalysisResult:
    """
    EOD analysis: send enriched stock data + live news to Claude and get
    structured buy/sell/hold recommendations with entry/exit/stop-loss levels.
    """
    client = _get_client()
    system_prompt = build_eod_system_prompt(trading_style, additional_context)
    user_message = _build_eod_user_message(stocks, news_block, sector_performance)

    logger.info(f"EOD analysis: sending {len(stocks)} stocks to Claude...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text
    parsed = _extract_json(response_text)
    return _parse_eod_result(parsed)
