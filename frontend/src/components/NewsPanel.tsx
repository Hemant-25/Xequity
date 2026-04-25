"use client";

import { ExternalLink, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NewsItem } from "@/lib/types";

interface NewsPanelProps {
  title: string;
  items: NewsItem[];
  loading: boolean;
  onRefresh: () => void;
  className?: string;
}

function timeAgo(publishedStr: string): string {
  if (!publishedStr) return "";
  try {
    const pub = new Date(publishedStr);
    const diff = Math.floor((Date.now() - pub.getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return "";
  }
}

export function NewsPanel({ title, items, loading, onRefresh, className }: NewsPanelProps) {
  return (
    <div
      className={cn("rounded-xl border flex flex-col", className)}
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <h3 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--muted)" }}>
          {title}
        </h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1 rounded opacity-50 hover:opacity-100 transition-opacity disabled:animate-spin"
          title="Refresh"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto divide-y" style={{ divideColor: "var(--border)" } as React.CSSProperties}>
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-10">
            <span
              className="w-5 h-5 border-2 rounded-full animate-spin"
              style={{ borderColor: "var(--border)", borderTopColor: "var(--accent)" }}
            />
          </div>
        ) : items.length === 0 ? (
          <p className="text-xs py-8 text-center" style={{ color: "var(--muted)" }}>
            No news items loaded.
          </p>
        ) : (
          items.map((item, idx) => (
            <a
              key={idx}
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col gap-1 px-4 py-3 hover:bg-white/5 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs leading-snug font-medium group-hover:text-[color:var(--accent)] transition-colors line-clamp-2">
                  {item.title}
                </span>
                <ExternalLink
                  size={11}
                  className="flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-60 transition-opacity"
                />
              </div>
              <div className="flex items-center gap-2">
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                  style={{ background: "var(--surface-2)", color: "var(--muted)" }}
                >
                  {item.source}
                </span>
                <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                  {timeAgo(item.published)}
                </span>
              </div>
            </a>
          ))
        )}
      </div>
    </div>
  );
}
