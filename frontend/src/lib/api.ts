import type {
  EODAnalysisRequest,
  EODAnalysisResult,
  NewsResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      // FastAPI wraps errors in { detail: "..." }
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      message = await res.text().catch(() => res.statusText);
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function runEODAnalysis(
  req: EODAnalysisRequest
): Promise<EODAnalysisResult> {
  return apiFetch<EODAnalysisResult>("/eod-analysis", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function fetchMarketNews(): Promise<NewsResponse> {
  return apiFetch<NewsResponse>("/news");
}

export async function fetchMacroNews(): Promise<NewsResponse> {
  return apiFetch<NewsResponse>("/news/macro");
}

export async function validateSymbol(
  symbol: string
): Promise<{ symbol: string; valid: boolean; price?: number }> {
  try {
    const data = await apiFetch<{ current_price?: number }>(`/stock/${symbol.toUpperCase()}`);
    return { symbol, valid: true, price: data.current_price };
  } catch {
    return { symbol, valid: false };
  }
}
