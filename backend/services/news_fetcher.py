"""
News Fetcher Service
====================
Aggregates financial news from RSS feeds and yfinance for:
  - Market-wide headlines (Indian financial media)
  - Macroeconomic / policy news (RBI, Budget, SEBI)
  - Stock-specific news (via yfinance)

All functions are synchronous with an in-memory TTL cache (30 min).
"""

import time
import logging
from datetime import datetime, timedelta, timezone

import feedparser
import yfinance as yf

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
_news_cache: dict[str, tuple[float, list]] = {}
NEWS_CACHE_TTL = 1800  # 30 minutes


# --------------------------------------------------------------------------- #
# RSS feed definitions
# --------------------------------------------------------------------------- #
MARKET_RSS_FEEDS = [
    {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rss.cms",
    },
    {
        "name": "Moneycontrol",
        "url": "https://www.moneycontrol.com/rss/MCtopnews.xml",
    },
    {
        "name": "Business Standard Markets",
        "url": "https://www.business-standard.com/rss/markets-106.rss",
    },
    {
        "name": "LiveMint Markets",
        "url": "https://www.livemint.com/rss/markets",
    },
]

MACRO_RSS_FEEDS = [
    {
        "name": "Economic Times Economy",
        "url": "https://economictimes.indiatimes.com/economy/rss.cms",
    },
    {
        "name": "Business Standard Economy",
        "url": "https://www.business-standard.com/rss/economy-policy-10101.rss",
    },
]


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _parse_feed(feed_url: str, max_items: int = 10) -> list[dict]:
    """Parse a single RSS feed and return normalised news items (last 48 h)."""
    try:
        feed = feedparser.parse(feed_url)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        items: list[dict] = []

        for entry in feed.entries[:max_items]:
            published: datetime | None = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            # Skip items older than 48 hours
            if published and published < cutoff:
                continue

            title = (entry.get("title") or "").strip()
            summary = (entry.get("summary") or "")[:300].strip()
            source = (feed.feed.get("title") or "Unknown")

            if title:
                items.append(
                    {
                        "title": title,
                        "summary": summary,
                        "published": published.isoformat() if published else None,
                        "source": source,
                    }
                )

        return items

    except Exception as e:
        logger.debug(f"Failed to parse RSS feed {feed_url}: {e}")
        return []


def _cached(key: str, fetcher, ttl: int = NEWS_CACHE_TTL) -> list[dict]:
    """Generic TTL-cache wrapper for news lists."""
    now = time.time()
    if key in _news_cache:
        cached_time, data = _news_cache[key]
        if now - cached_time < ttl:
            return data
    result = fetcher()
    _news_cache[key] = (now, result)
    return result


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def fetch_market_news(max_items_per_feed: int = 8) -> list[dict]:
    """
    Fetch latest Indian market headlines from RSS feeds.
    Returns up to 30 items, newest first, cached for 30 min.
    """
    def _fetch() -> list[dict]:
        all_items: list[dict] = []
        for feed_cfg in MARKET_RSS_FEEDS:
            all_items.extend(_parse_feed(feed_cfg["url"], max_items_per_feed))
        all_items.sort(key=lambda x: x.get("published") or "", reverse=True)
        return all_items[:30]

    return _cached("market_news", _fetch)


def fetch_macro_news(max_items: int = 8) -> list[dict]:
    """
    Fetch macroeconomic / policy news (RBI, Budget, SEBI, GDP).
    Returns up to 15 items, cached for 30 min.
    """
    def _fetch() -> list[dict]:
        all_items: list[dict] = []
        for feed_cfg in MACRO_RSS_FEEDS:
            all_items.extend(_parse_feed(feed_cfg["url"], max_items))
        all_items.sort(key=lambda x: x.get("published") or "", reverse=True)
        return all_items[:15]

    return _cached("macro_news", _fetch)


def fetch_stock_news(symbol: str, max_items: int = 5) -> list[dict]:
    """
    Fetch stock-specific news via yfinance.
    Returns up to `max_items` recent articles, cached for 30 min.
    """
    cache_key = f"stock_news_{symbol.upper()}"

    def _fetch() -> list[dict]:
        try:
            ticker = yf.Ticker(f"{symbol.upper()}.NS")
            raw_news = ticker.news or []
            items: list[dict] = []

            for item in raw_news[:max_items]:
                title = ""
                summary = ""
                published_iso: str | None = None

                # yfinance >= 0.2.40 wraps news in a 'content' list
                content = item.get("content") if isinstance(item, dict) else None
                if isinstance(content, list) and content:
                    first = content[0]
                    title = (first.get("title") or "").strip()
                    summary = (first.get("summary") or "")[:300].strip()
                    pub = first.get("pubDate") or item.get("providerPublishTime")
                else:
                    title = (item.get("title") or "").strip()
                    summary = (item.get("summary") or "")[:300].strip()
                    pub = item.get("providerPublishTime")

                if pub:
                    try:
                        ts = float(pub)
                        published_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                    except (TypeError, ValueError):
                        published_iso = str(pub)

                if title:
                    items.append(
                        {
                            "title": title,
                            "summary": summary,
                            "published": published_iso,
                            "source": "Yahoo Finance",
                        }
                    )

            return items

        except Exception as e:
            logger.debug(f"Could not fetch stock news for {symbol}: {e}")
            return []

    return _cached(cache_key, _fetch)


def fetch_all_news_for_symbols(
    symbols: list[str],
) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    """
    Convenience function: fetch market news, macro news, and per-symbol news in one call.
    Returns: (market_news, macro_news, {symbol: [news_items]})
    """
    market_news = fetch_market_news()
    macro_news = fetch_macro_news()
    stock_news_map: dict[str, list[dict]] = {}
    for sym in symbols:
        stock_news_map[sym.upper()] = fetch_stock_news(sym)

    return market_news, macro_news, stock_news_map


def format_news_for_prompt(
    market_news: list[dict],
    macro_news: list[dict],
    stock_news_map: dict[str, list[dict]],
) -> str:
    """
    Format all aggregated news into a structured block for the AI prompt.
    """
    lines: list[str] = ["## LATEST FINANCIAL NEWS & MARKET SENTIMENT\n"]

    if market_news:
        lines.append("### Market Headlines (Last 48 Hours)")
        for item in market_news[:12]:
            title = item.get("title", "")
            source = item.get("source", "")
            if title:
                lines.append(f"- [{source}] {title}")
        lines.append("")

    if macro_news:
        lines.append("### Macro / Policy News (RBI, Budget, SEBI, Economy)")
        for item in macro_news[:6]:
            title = item.get("title", "")
            source = item.get("source", "")
            if title:
                lines.append(f"- [{source}] {title}")
        lines.append("")

    if any(v for v in stock_news_map.values()):
        lines.append("### Stock-Specific News")
        for symbol, news_list in stock_news_map.items():
            if news_list:
                lines.append(f"**{symbol}:**")
                for item in news_list[:3]:
                    title = item.get("title", "")
                    if title:
                        lines.append(f"  - {title}")
        lines.append("")

    return "\n".join(lines)
