// -----------------------------------------------------------------------
// Shared type definitions mirroring backend Pydantic models (schemas.py)
// -----------------------------------------------------------------------

export type TradingStyle = "swing" | "longterm";

export type Verdict = "Strong Buy" | "Buy" | "Hold" | "Reduce" | "Sell";

export type Conviction = "High" | "Medium" | "Low";

export type NewsSentiment = "Positive" | "Neutral" | "Negative" | "Mixed";

// --------------- EOD Analysis ---------------

export interface EODAnalysisRequest {
  symbols: string[];
  trading_style: TradingStyle;
  additional_context?: string;
  include_news: boolean;
}

export interface EODStockRecommendation {
  symbol: string;
  current_price: number;
  recommendation: Verdict;
  entry_zone_low: number | null;
  entry_zone_high: number | null;
  stop_loss: number | null;
  target_1: number | null;
  target_2: number | null;
  risk_reward_ratio: number | null;
  conviction: Conviction | null;
  position_size_pct: number | null;
  rationale: string;
  key_catalysts: string | null;
  risk_factors: string | null;
  technical_setup: string | null;
  news_impact: string | null;
}

export interface EODAnalysisResult {
  analysis_date: string;
  market_outlook: string;
  news_sentiment: NewsSentiment | null;
  macro_context: string | null;
  top_picks: string[];
  stocks_to_avoid: string[];
  recommendations: EODStockRecommendation[];
}

// --------------- News ---------------

export interface NewsItem {
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
}

export interface NewsResponse {
  items: NewsItem[];
  fetched_at: string;
}

// --------------- Stock / Sector ---------------

export interface SectorPerformance {
  sector: string;
  change_pct: number;
}
