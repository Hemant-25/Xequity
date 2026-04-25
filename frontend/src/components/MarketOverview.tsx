"use client";

import type { EODAnalysisResult, NewsSentiment } from "@/lib/types";
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";

const SENTIMENT_CONFIG: Record<NewsSentiment, { color: string; label: string }> = {
  Positive: { color: "#22c55e", label: "Positive" },
  Negative: { color: "#ef4444", label: "Negative" },
  Neutral: { color: "#94a3b8", label: "Neutral" },
  Mixed: { color: "#f59e0b", label: "Mixed" },
};

interface MarketOverviewProps {
  result: EODAnalysisResult;
}

export function MarketOverview({ result }: MarketOverviewProps) {
  const sentCfg = result.news_sentiment
    ? SENTIMENT_CONFIG[result.news_sentiment]
    : null;

  const buys = result.recommendations.filter(
    (r) => r.recommendation === "Buy" || r.recommendation === "Strong Buy"
  ).length;
  const holds = result.recommendations.filter(
    (r) => r.recommendation === "Hold"
  ).length;
  const sells = result.recommendations.filter(
    (r) => r.recommendation === "Reduce" || r.recommendation === "Sell"
  ).length;

  return (
    <div
      className="rounded-xl border p-5 flex flex-col gap-4"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity size={16} style={{ color: "var(--accent)" }} />
        <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--muted)" }}>
          Market Overview
        </h2>
        <span className="ml-auto text-xs" style={{ color: "var(--muted)" }}>
          {result.analysis_date}
        </span>
      </div>

      {/* Signal distribution */}
      <div className="grid grid-cols-3 gap-2">
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "#0f2a1e" }}
        >
          <TrendingUp size={16} className="mx-auto mb-1" style={{ color: "#22c55e" }} />
          <div className="text-xl font-bold font-mono" style={{ color: "#22c55e" }}>{buys}</div>
          <div className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: "#4ade8077" }}>Buy</div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "#1c1a09" }}
        >
          <Minus size={16} className="mx-auto mb-1" style={{ color: "#f59e0b" }} />
          <div className="text-xl font-bold font-mono" style={{ color: "#f59e0b" }}>{holds}</div>
          <div className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: "#f59e0b77" }}>Hold</div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: "#1e0b0b" }}
        >
          <TrendingDown size={16} className="mx-auto mb-1" style={{ color: "#ef4444" }} />
          <div className="text-xl font-bold font-mono" style={{ color: "#ef4444" }}>{sells}</div>
          <div className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: "#ef444477" }}>Sell</div>
        </div>
      </div>

      {/* Market outlook */}
      <div>
        <div className="text-[10px] uppercase tracking-widest mb-1.5" style={{ color: "var(--muted)" }}>
          Market Outlook
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>
          {result.market_outlook}
        </p>
      </div>

      {/* News sentiment */}
      {sentCfg && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--muted)" }}>
            News Sentiment
          </span>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded"
            style={{ background: `${sentCfg.color}22`, color: sentCfg.color }}
          >
            {sentCfg.label}
          </span>
        </div>
      )}

      {/* Macro context */}
      {result.macro_context && (
        <div>
          <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: "var(--muted)" }}>
            Macro Context
          </div>
          <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            {result.macro_context}
          </p>
        </div>
      )}

      {/* Stocks to avoid */}
      {result.stocks_to_avoid.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-widest mb-1.5" style={{ color: "var(--muted)" }}>
            Stocks to Avoid
          </div>
          <div className="flex flex-wrap gap-1.5">
            {result.stocks_to_avoid.map((sym) => (
              <span
                key={sym}
                className="text-xs font-mono px-2 py-0.5 rounded"
                style={{ background: "#1e0b0b", color: "#ef4444", border: "1px solid #ef444433" }}
              >
                {sym}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
