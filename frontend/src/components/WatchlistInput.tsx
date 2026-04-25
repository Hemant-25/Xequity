"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { X, Plus, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TradingStyle } from "@/lib/types";

interface WatchlistInputProps {
  symbols: string[];
  onSymbolsChange: (symbols: string[]) => void;
  tradingStyle: TradingStyle;
  onTradingStyleChange: (style: TradingStyle) => void;
  additionalContext: string;
  onAdditionalContextChange: (ctx: string) => void;
  includeNews: boolean;
  onIncludeNewsChange: (val: boolean) => void;
  onAnalyse: () => void;
  loading: boolean;
}

export function WatchlistInput({
  symbols,
  onSymbolsChange,
  tradingStyle,
  onTradingStyleChange,
  additionalContext,
  onAdditionalContextChange,
  includeNews,
  onIncludeNewsChange,
  onAnalyse,
  loading,
}: WatchlistInputProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addSymbol = () => {
    const raw = input.trim().toUpperCase().replace(/\.NS$/, "");
    if (!raw || symbols.includes(raw) || symbols.length >= 20) return;
    onSymbolsChange([...symbols, raw]);
    setInput("");
    inputRef.current?.focus();
  };

  const removeSymbol = (sym: string) => {
    onSymbolsChange(symbols.filter((s) => s !== sym));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSymbol();
    }
    if (e.key === "Backspace" && input === "" && symbols.length > 0) {
      onSymbolsChange(symbols.slice(0, -1));
    }
  };

  return (
    <div
      className="rounded-xl border p-5 flex flex-col gap-4"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <TrendingUp size={18} style={{ color: "var(--accent)" }} />
        <h2 className="font-semibold text-sm tracking-wide uppercase" style={{ color: "var(--muted)" }}>
          Watchlist
        </h2>
        <span className="ml-auto text-xs" style={{ color: "var(--muted)" }}>
          {symbols.length} / 20 symbols
        </span>
      </div>

      {/* Symbol chips + input */}
      <div
        className="flex flex-wrap gap-2 min-h-[44px] rounded-lg border px-3 py-2 cursor-text"
        style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
        onClick={() => inputRef.current?.focus()}
      >
        {symbols.map((sym) => (
          <span
            key={sym}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-semibold"
            style={{
              background: "var(--accent-muted)",
              color: "#bfdbfe",
            }}
          >
            {sym}
            <button
              onClick={(e) => { e.stopPropagation(); removeSymbol(sym); }}
              className="opacity-60 hover:opacity-100 transition-opacity"
            >
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          onKeyDown={handleKeyDown}
          placeholder={symbols.length === 0 ? "Type NSE symbol e.g. RELIANCE, TCS…" : ""}
          disabled={symbols.length >= 20}
          className={cn(
            "flex-1 min-w-[120px] bg-transparent outline-none text-sm font-mono",
            "placeholder:text-[var(--muted)] text-[var(--foreground)]"
          )}
        />
        <button
          onClick={addSymbol}
          disabled={!input.trim()}
          className="ml-auto p-1 rounded opacity-60 hover:opacity-100 transition-opacity disabled:opacity-20"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Settings row */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Trading style */}
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
            Style
          </label>
          <div className="flex rounded-lg overflow-hidden border" style={{ borderColor: "var(--border)" }}>
            {(["swing", "longterm"] as TradingStyle[]).map((s) => (
              <button
                key={s}
                onClick={() => onTradingStyleChange(s)}
                className={cn(
                  "px-4 py-1.5 text-xs font-semibold capitalize transition-colors",
                  tradingStyle === s
                    ? "text-white"
                    : "hover:bg-white/5"
                )}
                style={
                  tradingStyle === s
                    ? { background: "var(--accent)" }
                    : { background: "var(--surface-2)", color: "var(--muted)" }
                }
              >
                {s === "longterm" ? "Long Term" : "Swing"}
              </button>
            ))}
          </div>
        </div>

        {/* Include news toggle */}
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
            Live News
          </label>
          <button
            onClick={() => onIncludeNewsChange(!includeNews)}
            className={cn(
              "w-12 h-6 rounded-full transition-colors relative",
            )}
            style={{
              background: includeNews ? "var(--accent)" : "var(--surface-2)",
              border: "1px solid var(--border)",
            }}
          >
            <span
              className="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all"
              style={{ left: includeNews ? "calc(100% - 22px)" : "2px" }}
            />
          </button>
        </div>
      </div>

      {/* Additional context */}
      <div className="flex flex-col gap-1">
        <label className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
          Additional Context <span className="normal-case">(optional)</span>
        </label>
        <textarea
          value={additionalContext}
          onChange={(e) => onAdditionalContextChange(e.target.value)}
          placeholder="RBI policy tomorrow, earnings today, any event…"
          rows={2}
          maxLength={2000}
          className="resize-none rounded-lg border px-3 py-2 text-sm outline-none focus:border-[color:var(--accent)] transition-colors"
          style={{
            background: "var(--surface-2)",
            borderColor: "var(--border)",
            color: "var(--foreground)",
          }}
        />
      </div>

      {/* Analyse button */}
      <button
        onClick={onAnalyse}
        disabled={symbols.length === 0 || loading}
        className={cn(
          "w-full py-3 rounded-lg font-semibold text-sm tracking-wide transition-all",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          "flex items-center justify-center gap-2"
        )}
        style={{
          background: loading ? "var(--accent-muted)" : "var(--accent)",
          color: "#fff",
        }}
      >
        {loading ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Analysing {symbols.length} stock{symbols.length !== 1 ? "s" : ""}…
          </>
        ) : (
          <>
            <TrendingUp size={16} />
            Run EOD Analysis
          </>
        )}
      </button>
    </div>
  );
}
