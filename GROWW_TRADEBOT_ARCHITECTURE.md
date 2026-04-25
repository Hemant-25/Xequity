# Groww EOD Tradebot — Architecture Design

**Purpose:** End-of-Day (EOD) trade signal engine for Indian equities (NSE) using the Groww API SDK.  
**Goal:** Analyze NSE price data + news sentiment → produce Buy / Sell / Hold triggers with entry zones, ATR-based stop-losses, and position sizing.  
**Constraints:** SEBI-compliant audit logging · Groww API rate limit of 10 req/sec enforced

---

## Directory Structure

```
groww_tradebot/
│
├── config.py                  ← Environment, constants, feature flags
├── main.py                    ← Scheduler entry point (EOD trigger at 15:25 IST)
│
├── core/
│   ├── rate_limiter.py        ← Token-bucket enforcer (10 req/sec hard cap)
│   ├── groww_client.py        ← Single authenticated Groww API gateway
│   ├── circuit_breaker.py     ← Hard kill-switch + soft error-rate breaker
│   └── exceptions.py          ← Domain-specific exception hierarchy
│
├── ingest/
│   ├── data_ingest.py         ← OHLCV + fundamentals via Groww + NSE fallback
│   ├── news_fetcher.py        ← RSS + yfinance stock/macro news aggregation
│   └── market_clock.py        ← NSE session state, holiday calendar, EOD timer
│
├── analysis/
│   ├── technicals.py          ← Pure-pandas: EMA/RSI/MACD/ADX/ATR/OBV/Volume
│   ├── sentiment_engine.py    ← News NLP → per-stock sentiment score (-1 to +1)
│   └── strategy_core.py       ← Signal aggregator → Buy / Sell / Hold
│
├── execution/
│   ├── risk_manager.py        ← Position sizing, exposure caps, drawdown limit
│   ├── order_manager.py       ← Order placement, status polling, slippage guard
│   └── portfolio_tracker.py   ← Holdings sync, MTM P&L, drawdown monitoring
│
├── compliance/
│   └── audit_logger.py        ← SEBI-compliant append-only structured log
│
└── models/
    ├── schemas.py             ← Pydantic models for every data contract
    └── enums.py               ← Signal, OrderType, OrderStatus, Side enums
```

---

## EOD Data Flow

```
15:25 IST trigger  (market_clock.py)
        │
        ▼
data_ingest.py ─────────────────────────────────────────┐
  [Groww API, rate-limited 10 req/sec, fallback yfinance]│
        │                                                │
        ▼                                                ▼
technicals.py                                   news_fetcher.py
  [MACD / ADX / ATR / OBV / Volume]             [RSS + yfinance]
        │                                                │
        └─────────────────────┬──────────────────────────┘
                              ▼
                    sentiment_engine.py
                      [score  -1 → +1]
                              │
                              ▼
                      strategy_core.py
                 [Buy/Sell/Hold + ATR stop-loss + R:R]
                              │
                              ▼
                      risk_manager.py
                 [size, exposure, drawdown checks]
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
          APPROVED                       REJECTED
               │                             │
               ▼                             ▼
       order_manager.py               audit_logger.py
  [place → poll → confirm]        [RISK_REJECTED event]
               │
               ▼
       audit_logger.py
  [ORDER_PLACED + ORDER_FILLED]
```

---

## Module Responsibilities

### `config.py`
- Loads from `.env`: `GROWW_API_KEY`, `GROWW_CLIENT_ID`, `ANTHROPIC_API_KEY`
- Key constants:
  - `MAX_RATE_RPS = 10`
  - `MAX_SINGLE_STOCK_PCT = 10.0`   (max % of portfolio in one stock)
  - `MAX_SECTOR_PCT = 30.0`
  - `DAILY_LOSS_LIMIT_PCT = 2.0`
  - `AUDIT_LOG_DIR = "./logs/audit"`
- Feature flag: `DRY_RUN = True` — paper-trade mode; no real orders placed until explicitly set to `False`

---

### `core/rate_limiter.py`
- **Token-bucket algorithm** — replenishes 10 tokens/second
- Async-safe using `asyncio.Semaphore` + timestamp-based refill
- All Groww API calls must acquire a token before executing
- On exhaustion: sleep until next replenish window (does not raise an error)
- Exposes a `@rate_limited` decorator applied at the `groww_client.py` level

### `core/groww_client.py`
- Single authenticated client wrapping the `growwapi` SDK
- All methods pass through `rate_limiter` **and** `circuit_breaker`
- Handles OAuth token refresh transparently
- Exposed methods:
  - `get_quote(symbol)` → current price + OHLC
  - `get_holdings()` → current portfolio state
  - `place_order(request)` → returns `order_id`
  - `get_order_status(order_id)` → polling
  - `cancel_order(order_id)`
- **Never** imported directly by analysis modules — only by execution modules

### `core/circuit_breaker.py`
- **Hard kill-switch:** reads `KILL_SWITCH.flag`; if present, all order placement halts immediately regardless of state
- **Soft breaker:** if API error rate > 30% in a 60-second window → pause all calls for 5 minutes, then auto-recover
- States: `CLOSED` (normal) → `OPEN` (halted) → `HALF_OPEN` (single test probe)
- All state transitions logged to `audit_logger`

### `core/exceptions.py`
Hierarchy:
```
TradebotError
├── RateLimitError
├── CircuitBreakerOpenError
├── KillSwitchError
├── RiskRejectionError
├── OrderPlacementError
│   ├── OrderRejectedError
│   └── OrderTimeoutError
└── DataFetchError
```

---

### `ingest/data_ingest.py`
- Fetches EOD OHLCV for watchlist from Groww API (`/v1/stocks/quote`)
- Falls back to yfinance `.NS` symbols if Groww returns stale/missing data
- Parallel fetches via `asyncio.gather` with bounded concurrency (≤ 5 simultaneous calls to respect rate limit)
- Fetches fundamentals: PE, D/E, ROE, market cap
- Returns: `list[EnrichedStockData]`

### `ingest/news_fetcher.py`
- RSS feed sources:
  - Economic Times Markets
  - Moneycontrol Top News
  - Business Standard Markets
  - LiveMint Markets
- Macro/policy feed: ET Economy (RBI, SEBI, Budget, GDP)
- Per-stock news via yfinance (consumes **zero** Groww rate-limit tokens)
- 30-minute in-memory TTL cache per symbol
- Output: `MarketNewsBundle(market_news, macro_news, stock_news_map)`

### `ingest/market_clock.py`
- NSE session: 09:15–15:30 IST (Asia/Kolkata)
- NSE holiday calendar loaded from bundled `nse_holidays.json`, updatable annually
- Key methods:
  - `is_trading_day() → bool`
  - `is_market_open() → bool`
  - `minutes_to_close() → int`
- **EOD trigger schedule:**
  - `15:25 IST` — pre-close analysis run (live price data)
  - `15:35 IST` — post-close final signal confirmation

---

### `analysis/technicals.py`
*(already implemented in `backend/services/technicals.py` — pure pandas/numpy)*

Indicators computed:
| Indicator | Parameters | Signal Derived |
|---|---|---|
| EMA | 50, 200 | Bullish / Bearish / Weakening |
| RSI | 14 | Overbought (>70) / Oversold (<30) |
| MACD | 12/26/9 | Bullish Crossover / Bearish Crossover / Momentum |
| ADX | 14 | Strong Trend (>25) / Moderate (20–25) / Ranging (<20) |
| ATR | 14 | Stop-loss sizing (1.5× ATR below entry) |
| Bollinger Bands | 20, 2σ | Band squeeze / breakout |
| Stochastic RSI | 14, K=3 | Fine entry timing |
| OBV | — | Bullish / Bearish accumulation |
| Volume Ratio | vs 20-day avg | Surge flag (>1.5×) |
| Pivot S/R | Classic, last 20 days | Support / Resistance levels |

### `analysis/sentiment_engine.py`
- Input: `MarketNewsBundle` from `news_fetcher.py`
- Pipeline per stock:
  1. Filter headlines mentioning the symbol or company name
  2. Score using an Indian-market keyword lexicon:
     - **Bull keywords:** buyback, order win, capacity expansion, beat estimates, upgrade, outperform, FII buying, government order, debt-free
     - **Bear keywords:** margin pressure, downgrade, underperform, promoter pledge, DII selling, debt increase, loss, write-off, SEBI probe
  3. Weight by recency: last 2h → ×3, last 6h → ×2, last 24h → ×1
  4. High-impact event boost ×2: RBI rate decision, earnings announcement, block deal
  5. Clamp to `[-1.0, +1.0]`
- Output: `dict[symbol, SentimentResult(score, label, top_headlines)]`

### `analysis/strategy_core.py`
The **only file** that produces actionable trading signals.

**Signal conditions:**

| Signal | Technical (must all match) | Sentiment | Fundamental filter |
|---|---|---|---|
| **Strong Buy** | Price > EMA50 > EMA200, MACD bullish crossover, ADX > 25, volume surge ≥ 1.5× | score ≥ +0.3 | ROE > 15%, D/E < 1 |
| **Buy** | Price > EMA50, MACD histogram positive, RSI 40–65 | score ≥ 0 | No red flags |
| **Hold** | Mixed / sideways technicals | Any | — |
| **Reduce** | Price < EMA50, MACD histogram falling | score ≤ −0.1 | — |
| **Sell** | Price < EMA50 < EMA200, MACD bearish | score ≤ −0.3 OR fundamental deterioration |

- **Mandatory R:R filter:** discard any Buy signal where Risk:Reward < 2.0
- **ATR stop-loss:** `stop_loss = entry_price − (1.5 × ATR)`
- Output: `list[TradeSignal]`

---

### `execution/risk_manager.py`
**Pre-trade checks** (all must pass before order placement):

| Check | Rule |
|---|---|
| Single-stock exposure | ≤ 10% of total portfolio value |
| Sector concentration | ≤ 30% of portfolio in one sector |
| Cash buffer | Always maintain ≥ 5% cash |
| Daily loss limit | If MTM drawdown > 2%, halt all BUYs for the day |
| Position duplication | Do not add to a position already at full size |

- Position sizing: Kelly fraction based on R:R, capped at 8% per trade
- Output: `RiskApproval(approved, suggested_qty, rejection_reason)`

### `execution/order_manager.py`
- Receives `TradeSignal` + `RiskApproval`
- Order ID scheme: `EOD-{YYYY-MM-DD}-{SYMBOL}-{UUID8}` (traceable, unique)
- Flow:
  1. Check `DRY_RUN` flag — if True, log hypothetical order and exit
  2. Log to `audit_logger` **before** placing (pre-trade record)
  3. Place via `groww_client.place_order()`
  4. Poll `get_order_status()` every 2 seconds, up to 30 seconds
  5. Log final status (post-trade record)
  6. On partial fill or rejection: log + alert, do **not** auto-retry
- Order types: `LIMIT` (default for entries), `MARKET` (only for stop-loss triggers)
- Rejects all orders outside NSE trading hours (enforced via `market_clock`)

### `execution/portfolio_tracker.py`
- Syncs holdings from Groww at EOD
- Computes MTM P&L per position and aggregate portfolio
- Tracks which open positions were generated by which signal run
- Feeds realized P&L to `risk_manager` daily drawdown counter

---

### `compliance/audit_logger.py`

**Regulatory basis:** SEBI Circular — Framework for Algorithmic Trading (2021 & 2023 updates)

- Format: **append-only newline-delimited JSON** (`.ndjson`) — never modified, never deleted
- Daily rotation: `audit_YYYY-MM-DD.ndjson`
- Every record contains:

| Field | Description |
|---|---|
| `log_id` | UUID v4 |
| `timestamp_ist` | ISO 8601 (Asia/Kolkata) |
| `event_type` | See event types below |
| `symbol` | NSE symbol |
| `exchange` | Always `NSE` |
| `isin` | ISIN code |
| `order_id` | Groww order ID |
| `algo_order_id` | Internal `EOD-{date}-{symbol}-{uuid8}` |
| `order_type` | `LIMIT` / `MARKET` / `SL` / `SL_M` |
| `side` | `BUY` / `SELL` |
| `qty` | Number of shares |
| `price` | Limit price in INR |
| `signal_rationale` | Full text rationale from `strategy_core` |
| `risk_approval_summary` | Position size, checks passed/failed |
| `checksum` | SHA-256 hash of the record (tamper detection) |

**Event types:**
- `SIGNAL_GENERATED`
- `RISK_APPROVED`
- `RISK_REJECTED`
- `ORDER_PLACED`
- `ORDER_FILLED`
- `ORDER_PARTIAL_FILL`
- `ORDER_REJECTED`
- `ORDER_CANCELLED`
- `KILL_SWITCH_ACTIVATED`
- `CIRCUIT_BREAKER_OPEN`

---

### `models/enums.py`

```
Signal:              Strong Buy | Buy | Hold | Reduce | Sell
Conviction:          High | Medium | Low
OrderSide:           BUY | SELL
OrderType:           LIMIT | MARKET | SL | SL_M
OrderStatus:         PENDING | OPEN | COMPLETE | REJECTED | CANCELLED
CircuitBreakerState: CLOSED | OPEN | HALF_OPEN
```

### `models/schemas.py`

| Model | Used by |
|---|---|
| `StockQuote` | `data_ingest` → `technicals` |
| `EnrichedStockData` | `data_ingest` → `strategy_core` |
| `TechnicalData` | `technicals` → `strategy_core` |
| `SentimentResult` | `sentiment_engine` → `strategy_core` |
| `TradeSignal` | `strategy_core` → `risk_manager` → `order_manager` |
| `RiskApproval` | `risk_manager` → `order_manager` |
| `OrderRequest` | `order_manager` → `groww_client` |
| `OrderResponse` | `groww_client` → `order_manager` |
| `AuditRecord` | `audit_logger` (all modules write here) |
| `MarketNewsBundle` | `news_fetcher` → `sentiment_engine` |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Rate-limit algorithm | Token bucket (not leaky bucket) | Correctly handles burst; Groww enforces per-second windows |
| Sentiment engine | Keyword lexicon, not LLM | Deterministic, auditable, zero latency — SEBI requires explainable rationale |
| LLM role | Optional second-opinion in `strategy_core` | Rule-based signal is primary (auditable); Claude adds contextual commentary only |
| Default order type | `LIMIT` | Avoids slippage in thin EOD liquidity |
| Kill-switch mechanism | File-based `KILL_SWITCH.flag` | Works even if Python process is degraded; `touch KILL_SWITCH.flag` halts everything |
| Default mode | `DRY_RUN = True` | No real money at risk until explicitly overridden |
| Order ID format | `EOD-{date}-{symbol}-{uuid8}` | Instantly traceable to algo run + stock |
| Audit log format | Append-only NDJSON + SHA-256 checksum | Tamper-evident, regulator-readable, machine-parseable |

---

## Recommended Build Order

Build in this sequence to avoid circular dependencies:

```
1. models/enums.py
2. models/schemas.py
3. core/exceptions.py
4. core/rate_limiter.py
5. core/circuit_breaker.py
6. core/groww_client.py
7. compliance/audit_logger.py          ← must exist before any execution code
8. ingest/market_clock.py
9. ingest/news_fetcher.py
10. ingest/data_ingest.py
11. analysis/technicals.py             ← already implemented in backend/services/
12. analysis/sentiment_engine.py
13. analysis/strategy_core.py
14. execution/risk_manager.py
15. execution/order_manager.py
16. execution/portfolio_tracker.py
17. config.py
18. main.py
```

---

## Environment Variables Required

```env
# Groww API
GROWW_API_KEY=your_api_key_here
GROWW_CLIENT_ID=your_client_id_here

# Anthropic (optional — for LLM second-opinion layer)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Safety
DRY_RUN=true
AUDIT_LOG_DIR=./logs/audit

# Risk limits (override defaults)
MAX_SINGLE_STOCK_PCT=10.0
MAX_SECTOR_PCT=30.0
DAILY_LOSS_LIMIT_PCT=2.0
```

---

## SEBI Compliance Notes

1. **Audit trail is mandatory** — every signal, every risk decision, every order (placed or rejected) must be logged before and after the event.
2. **Unique algo order IDs** — SEBI requires all algorithmic orders to carry a unique identifier traceable to the strategy.
3. **Kill-switch** — SEBI mandates a real-time kill-switch capability for all algo strategies.
4. **No market orders except SL triggers** — reduces market impact and is considered best practice under SEBI guidelines.
5. **Log retention** — SEBI requires algo trade records to be retained for **5 years**. Back up `logs/audit/` to cold storage daily.
6. **Testing in paper-trade mode (`DRY_RUN=True`) before going live is strongly recommended.**
