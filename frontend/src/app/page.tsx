"use client";

import { useState, useEffect, useCallback } from "react";
import { runEODAnalysis, fetchMarketNews, fetchMacroNews } from "@/lib/api";
import type {
  EODAnalysisResult,
  NewsItem,
  TradingStyle,
} from "@/lib/types";
import { WatchlistInput } from "@/components/WatchlistInput";
import { RecommendationCard } from "@/components/RecommendationCard";
import { MarketOverview } from "@/components/MarketOverview";
import { NewsPanel } from "@/components/NewsPanel";
import { AlertTriangle, BarChart2 } from "lucide-react";

type SortKey = "verdict" | "conviction" | "rr" | "symbol";

const VERDICT_ORDER: Record<string, number> = {
  "Strong Buy": 0,
  "Buy": 1,
  "Hold": 2,
  "Reduce": 3,
  "Sell": 4,
};

export default function Home() {
  // ── Watchlist form state ──
  const [symbols, setSymbols] = useState<string[]>([]);
  const [tradingStyle, setTradingStyle] = useState<TradingStyle>("swing");
  const [additionalContext, setAdditionalContext] = useState("");
  const [includeNews, setIncludeNews] = useState(true);

  // ── Analysis state ──
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<EODAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // ── News state ──
  const [marketNews, setMarketNews] = useState<NewsItem[]>([]);
  const [macroNews, setMacroNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);

  // ── Sort ──
  const [sortKey, setSortKey] = useState<SortKey>("verdict");

  // ── Fetch news ──
  const loadNews = useCallback(async () => {
    setNewsLoading(true);
    try {
      const [mkt, macro] = await Promise.all([fetchMarketNews(), fetchMacroNews()]);
      setMarketNews(mkt.items ?? []);
      setMacroNews(macro.items ?? []);
    } catch {
      // silently fail — news is non-blocking
    } finally {
      setNewsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNews();
  }, [loadNews]);

  // ── Run EOD analysis ──
  const handleAnalyse = async () => {
    if (symbols.length === 0) return;
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const result = await runEODAnalysis({
        symbols,
        trading_style: tradingStyle,
        additional_context: additionalContext || undefined,
        include_news: includeNews,
      });
      setAnalysisResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setAnalysisError(msg);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // ── Sorted recommendations ──
  const sortedRecs = analysisResult
    ? [...analysisResult.recommendations].sort((a, b) => {
        if (sortKey === "verdict") {
          return (VERDICT_ORDER[a.recommendation] ?? 99) - (VERDICT_ORDER[b.recommendation] ?? 99);
        }
        if (sortKey === "conviction") {
          const cOrder: Record<string, number> = { High: 0, Medium: 1, Low: 2 };
          return (cOrder[a.conviction ?? ""] ?? 99) - (cOrder[b.conviction ?? ""] ?? 99);
        }
        if (sortKey === "rr") {
          return (b.risk_reward_ratio ?? 0) - (a.risk_reward_ratio ?? 0);
        }
        return a.symbol.localeCompare(b.symbol);
      })
    : [];

  const topPickSet = new Set(analysisResult?.top_picks ?? []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top nav ── */}
      <header
        className="sticky top-0 z-20 flex items-center gap-3 px-6 py-3 border-b"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <BarChart2 size={20} style={{ color: "var(--accent)" }} />
        <span className="font-bold text-sm tracking-wide">Tradebot</span>
        <span
          className="text-[10px] px-2 py-0.5 rounded font-medium"
          style={{ background: "var(--surface-2)", color: "var(--muted)" }}
        >
          NSE/BSE · AI-Powered EOD
        </span>
      </header>

      {/* ── Main layout ── */}
      <main className="flex-1 grid grid-cols-1 xl:grid-cols-[340px_1fr_280px] gap-0">
        {/* ── Left panel: input ── */}
        <aside
          className="flex flex-col gap-4 p-4 border-r overflow-y-auto xl:max-h-[calc(100vh-49px)] xl:sticky xl:top-[49px]"
          style={{ borderColor: "var(--border)" }}
        >
          <WatchlistInput
            symbols={symbols}
            onSymbolsChange={setSymbols}
            tradingStyle={tradingStyle}
            onTradingStyleChange={setTradingStyle}
            additionalContext={additionalContext}
            onAdditionalContextChange={setAdditionalContext}
            includeNews={includeNews}
            onIncludeNewsChange={setIncludeNews}
            onAnalyse={handleAnalyse}
            loading={analysisLoading}
          />
        </aside>

        {/* ── Centre: recommendations ── */}
        <section className="flex flex-col gap-4 p-4 overflow-y-auto">
          {analysisError && (
            <div
              className="flex items-start gap-3 px-4 py-3 rounded-xl border text-sm"
              style={{ background: "#1e0b0b", borderColor: "#ef444455", color: "#ef4444" }}
            >
              <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold mb-0.5">Analysis failed</div>
                <div className="text-xs opacity-80">{analysisError}</div>
              </div>
            </div>
          )}

          {analysisLoading && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <div
                className="w-10 h-10 border-2 rounded-full animate-spin"
                style={{ borderColor: "var(--border)", borderTopColor: "var(--accent)" }}
              />
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Claude is analysing {symbols.length} stock{symbols.length !== 1 ? "s" : ""}…
              </p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Fetching live data · Computing indicators · Aggregating news
              </p>
            </div>
          )}

          {!analysisLoading && analysisResult && (
            <>
              {/* Sort bar */}
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: "var(--muted)" }}>Sort:</span>
                {(["verdict", "conviction", "rr", "symbol"] as SortKey[]).map((k) => (
                  <button
                    key={k}
                    onClick={() => setSortKey(k)}
                    className="text-xs px-2.5 py-1 rounded capitalize transition-colors"
                    style={
                      sortKey === k
                        ? { background: "var(--accent)", color: "#fff" }
                        : { background: "var(--surface)", color: "var(--muted)", border: "1px solid var(--border)" }
                    }
                  >
                    {k === "rr" ? "Risk/Reward" : k}
                  </button>
                ))}
              </div>

              {/* Cards */}
              <div className="flex flex-col gap-3">
                {sortedRecs.map((rec) => (
                  <RecommendationCard
                    key={rec.symbol}
                    rec={rec}
                    isTopPick={topPickSet.has(rec.symbol)}
                  />
                ))}
              </div>
            </>
          )}

          {!analysisLoading && !analysisResult && !analysisError && (
            <div
              className="flex flex-col items-center justify-center py-24 text-center gap-3"
              style={{ color: "var(--muted)" }}
            >
              <BarChart2 size={40} style={{ color: "var(--border)" }} />
              <p className="text-sm font-medium">Add symbols and run EOD analysis</p>
              <p className="text-xs max-w-xs">
                Enter NSE symbols in the watchlist panel, choose your trading style, then click{" "}
                <span style={{ color: "var(--accent)" }}>Run EOD Analysis</span>.
              </p>
            </div>
          )}
        </section>

        {/* ── Right panel: market overview + news ── */}
        <aside
          className="flex flex-col gap-4 p-4 border-l overflow-y-auto xl:max-h-[calc(100vh-49px)] xl:sticky xl:top-[49px]"
          style={{ borderColor: "var(--border)" }}
        >
          {analysisResult && (
            <MarketOverview result={analysisResult} />
          )}

          <NewsPanel
            title="Market News"
            items={marketNews}
            loading={newsLoading}
            onRefresh={loadNews}
            className="flex-1 min-h-[300px] max-h-[400px]"
          />
          <NewsPanel
            title="Macro / Policy"
            items={macroNews}
            loading={newsLoading}
            onRefresh={loadNews}
            className="min-h-[200px] max-h-[300px]"
          />
        </aside>
      </main>
    </div>
  );
}
