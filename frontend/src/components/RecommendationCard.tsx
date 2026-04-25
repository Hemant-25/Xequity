"use client";

import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
  Zap,
  Shield,
  Target,
  AlertTriangle,
  Newspaper,
  BarChart2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency, formatNumber } from "@/lib/utils";
import type { EODStockRecommendation, Verdict, Conviction } from "@/lib/types";

// ─── Verdict colours ─────────────────────────────────────────────────────────
const VERDICT_CONFIG: Record<
  Verdict,
  { label: string; bg: string; text: string; border: string; Icon: React.FC<{ size?: number }> }
> = {
  "Strong Buy": {
    label: "Strong Buy",
    bg: "#052e16",
    text: "#4ade80",
    border: "#16a34a",
    Icon: ({ size = 14 }) => <TrendingUp size={size} />,
  },
  Buy: {
    label: "Buy",
    bg: "#0f2a1e",
    text: "#22c55e",
    border: "#22c55e",
    Icon: ({ size = 14 }) => <TrendingUp size={size} />,
  },
  Hold: {
    label: "Hold",
    bg: "#1c1a09",
    text: "#f59e0b",
    border: "#f59e0b",
    Icon: ({ size = 14 }) => <Minus size={size} />,
  },
  Reduce: {
    label: "Reduce",
    bg: "#1e140b",
    text: "#f97316",
    border: "#f97316",
    Icon: ({ size = 14 }) => <TrendingDown size={size} />,
  },
  Sell: {
    label: "Sell",
    bg: "#1e0b0b",
    text: "#ef4444",
    border: "#ef4444",
    Icon: ({ size = 14 }) => <TrendingDown size={size} />,
  },
};

const CONVICTION_COLORS: Record<Conviction, string> = {
  High: "#22c55e",
  Medium: "#f59e0b",
  Low: "#ef4444",
};

// ─── Stat box ─────────────────────────────────────────────────────────────────
function StatBox({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div
      className="flex flex-col gap-0.5 rounded-lg p-3"
      style={{ background: "var(--surface-2)" }}
    >
      <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--muted)" }}>
        {label}
      </span>
      <span className="text-sm font-bold font-mono" style={{ color: color ?? "var(--foreground)" }}>
        {value}
      </span>
      {sub && (
        <span className="text-[10px]" style={{ color: "var(--muted)" }}>
          {sub}
        </span>
      )}
    </div>
  );
}

// ─── Section ──────────────────────────────────────────────────────────────────
function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5">
        <span style={{ color: "var(--muted)" }}>{icon}</span>
        <span className="text-[11px] uppercase tracking-widest font-semibold" style={{ color: "var(--muted)" }}>
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

// ─── Risk/Reward bar ──────────────────────────────────────────────────────────
function RRBar({ rr }: { rr: number }) {
  // Cap at 5:1 for visual scaling
  const pct = Math.min((rr / 5) * 100, 100);
  const color = rr >= 2 ? "#22c55e" : rr >= 1 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs font-mono font-semibold" style={{ color }}>
        {rr.toFixed(1)}:1
      </span>
    </div>
  );
}

// ─── Main Card ────────────────────────────────────────────────────────────────
interface RecommendationCardProps {
  rec: EODStockRecommendation;
  isTopPick?: boolean;
}

export function RecommendationCard({ rec, isTopPick }: RecommendationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const cfg = VERDICT_CONFIG[rec.recommendation];
  const { Icon } = cfg;

  const hasEntry = rec.entry_zone_low != null && rec.entry_zone_high != null;

  return (
    <div
      className="rounded-xl border transition-all"
      style={{
        background: "var(--surface)",
        borderColor: isTopPick ? cfg.border : "var(--border)",
        boxShadow: isTopPick ? `0 0 0 1px ${cfg.border}22` : undefined,
      }}
    >
      {/* ── Top bar ── */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Verdict badge */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold"
          style={{ background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}` }}
        >
          <Icon size={12} />
          {cfg.label}
        </div>

        {/* Symbol + price */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-bold text-base font-mono">{rec.symbol}</span>
            {isTopPick && (
              <span
                className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider"
                style={{ background: "#422006", color: "#fb923c" }}
              >
                Top Pick
              </span>
            )}
          </div>
          <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
            {formatCurrency(rec.current_price)}
          </span>
        </div>

        {/* Conviction + position size */}
        <div className="ml-auto flex items-center gap-3">
          {rec.conviction && (
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--muted)" }}>
                Conviction
              </span>
              <span
                className="text-xs font-bold"
                style={{ color: CONVICTION_COLORS[rec.conviction] }}
              >
                {rec.conviction}
              </span>
            </div>
          )}
          {rec.position_size_pct != null && (
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--muted)" }}>
                Size
              </span>
              <span className="text-xs font-semibold font-mono">
                {rec.position_size_pct.toFixed(0)}%
              </span>
            </div>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1 rounded opacity-50 hover:opacity-100 transition-opacity"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* ── Key levels ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 px-4 pb-3">
        {hasEntry && (
          <StatBox
            label="Entry Zone"
            value={`${formatCurrency(rec.entry_zone_low)} – ${formatCurrency(rec.entry_zone_high)}`}
            color="var(--accent)"
          />
        )}
        {rec.stop_loss != null && (
          <StatBox
            label="Stop Loss"
            value={formatCurrency(rec.stop_loss)}
            color="#ef4444"
          />
        )}
        {rec.target_1 != null && (
          <StatBox
            label="Target 1"
            value={formatCurrency(rec.target_1)}
            color="#22c55e"
          />
        )}
        {rec.target_2 != null && (
          <StatBox
            label="Target 2"
            value={formatCurrency(rec.target_2)}
            sub="Stretch target"
            color="#4ade80"
          />
        )}
      </div>

      {/* R:R bar */}
      {rec.risk_reward_ratio != null && (
        <div className="px-4 pb-3">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--muted)" }}>
              Risk / Reward
            </span>
            <RRBar rr={rec.risk_reward_ratio} />
          </div>
        </div>
      )}

      {/* Rationale (always visible) */}
      <div
        className="mx-4 mb-3 px-3 py-2 rounded-lg text-sm leading-relaxed"
        style={{ background: "var(--surface-2)", color: "var(--foreground)" }}
      >
        {rec.rationale}
      </div>

      {/* ── Expanded details ── */}
      {expanded && (
        <div className="px-4 pb-4 flex flex-col gap-4 border-t" style={{ borderColor: "var(--border)" }}>
          <div className="pt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {rec.technical_setup && (
              <Section icon={<BarChart2 size={12} />} title="Technical Setup">
                <p className="text-xs leading-relaxed" style={{ color: "var(--foreground)" }}>
                  {rec.technical_setup}
                </p>
              </Section>
            )}
            {rec.key_catalysts && (
              <Section icon={<Zap size={12} />} title="Key Catalysts">
                <p className="text-xs leading-relaxed" style={{ color: "var(--foreground)" }}>
                  {rec.key_catalysts}
                </p>
              </Section>
            )}
            {rec.risk_factors && (
              <Section icon={<AlertTriangle size={12} />} title="Risk Factors">
                <p className="text-xs leading-relaxed" style={{ color: "#ef4444" }}>
                  {rec.risk_factors}
                </p>
              </Section>
            )}
            {rec.news_impact && (
              <Section icon={<Newspaper size={12} />} title="News Impact">
                <p className="text-xs leading-relaxed" style={{ color: "var(--foreground)" }}>
                  {rec.news_impact}
                </p>
              </Section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
