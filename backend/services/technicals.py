"""
Technical Indicators — pure pandas/numpy implementation.

No external TA library dependency. All computations use standard
pandas rolling/ewm operations so the code works on any Python env.
"""

import pandas as pd
import numpy as np
from models.schemas import TechnicalData
import logging

logger = logging.getLogger(__name__)


# =========================================================================== #
# Low-level indicator helpers
# =========================================================================== #

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=length - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(com=length - 1, adjust=False).mean()


def _macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _adx(
    high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (adx, plus_di, minus_di)."""
    high_diff = high.diff()
    low_diff = -low.diff()

    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0.0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0.0)

    tr = _true_range(high, low, close)
    atr = tr.ewm(com=length - 1, adjust=False).mean()

    plus_di = 100 * plus_dm.ewm(com=length - 1, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(com=length - 1, adjust=False).mean() / atr.replace(0, np.nan)

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(com=length - 1, adjust=False).mean()
    return adx, plus_di, minus_di


def _bbands(
    series: pd.Series, length: int = 20, std_mult: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower)."""
    mid = series.rolling(length).mean()
    std = series.rolling(length).std()
    return mid + std_mult * std, mid, mid - std_mult * std


def _stoch_rsi_k(series: pd.Series, rsi_length: int = 14, smooth_k: int = 3) -> pd.Series:
    rsi = _rsi(series, rsi_length)
    rsi_min = rsi.rolling(rsi_length).min()
    rsi_max = rsi.rolling(rsi_length).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch = 100 * (rsi - rsi_min) / rsi_range
    return stoch.rolling(smooth_k).mean()


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume).cumsum()


# =========================================================================== #
# Main public function
# =========================================================================== #

def compute_technicals(df: pd.DataFrame) -> TechnicalData:
    """
    Compute a full suite of technical indicators from an OHLCV DataFrame.

    Basic     : EMA 50/200, RSI 14, Bollinger Bands 20, Pivot S/R
    Advanced  : MACD 12/26/9, ADX 14, ATR 14, Stochastic RSI 14,
                OBV direction, Volume ratio / surge detection
    """
    if df.empty or len(df) < 20:
        raise ValueError(
            "Insufficient data for technical analysis (need at least 20 trading days)"
        )

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume: pd.Series | None = df.get("Volume")
    current_price = float(close.iloc[-1])

    # ------------------------------------------------------------------ #
    # EMA 50 / 200
    # ------------------------------------------------------------------ #
    ema_50: float | None = None
    ema_200: float | None = None
    ema_signal = "Neutral"
    price_vs_ema200: str | None = None

    if len(df) >= 50:
        ema_50 = round(float(_ema(close, 50).iloc[-1]), 2)
    if len(df) >= 200:
        ema_200 = round(float(_ema(close, 200).iloc[-1]), 2)

    if ema_50 and ema_200:
        if current_price > ema_50 > ema_200:
            ema_signal = "Bullish"
        elif current_price < ema_50 < ema_200:
            ema_signal = "Bearish"
        elif ema_50 > ema_200:
            ema_signal = "Bullish (weakening)" if current_price < ema_50 else "Bullish"
        else:
            ema_signal = "Bearish (recovering)" if current_price > ema_50 else "Bearish"

    if ema_200:
        price_vs_ema200 = "Above" if current_price > ema_200 else "Below"

    # ------------------------------------------------------------------ #
    # RSI 14
    # ------------------------------------------------------------------ #
    rsi_14: float | None = None
    rsi_signal = "Neutral"

    rsi_series = _rsi(close, 14)
    if not rsi_series.empty and pd.notna(rsi_series.iloc[-1]):
        rsi_14 = round(float(rsi_series.iloc[-1]), 2)
        if rsi_14 > 70:
            rsi_signal = "Overbought"
        elif rsi_14 < 30:
            rsi_signal = "Oversold"
        elif rsi_14 > 60:
            rsi_signal = "Bullish"
        elif rsi_14 < 40:
            rsi_signal = "Bearish"

    # ------------------------------------------------------------------ #
    # Bollinger Bands (20, 2-sigma)
    # ------------------------------------------------------------------ #
    bb_upper: float | None = None
    bb_lower: float | None = None

    if len(df) >= 20:
        bbu, _, bbl = _bbands(close, 20, 2.0)
        if pd.notna(bbu.iloc[-1]):
            bb_upper = round(float(bbu.iloc[-1]), 2)
            bb_lower = round(float(bbl.iloc[-1]), 2)

    # ------------------------------------------------------------------ #
    # Support / Resistance — Classic Pivot from last 20 sessions
    # ------------------------------------------------------------------ #
    support_level, resistance_level = _compute_pivot_levels(df)

    # ------------------------------------------------------------------ #
    # Period returns
    # ------------------------------------------------------------------ #
    weekly_change_pct: float | None = None
    monthly_change_pct: float | None = None

    if len(df) >= 5:
        ref = float(close.iloc[-min(5, len(df))])
        if ref:
            weekly_change_pct = round((current_price - ref) / ref * 100, 2)
    if len(df) >= 22:
        ref = float(close.iloc[-min(22, len(df))])
        if ref:
            monthly_change_pct = round((current_price - ref) / ref * 100, 2)

    # ================================================================== #
    # ADVANCED INDICATORS
    # ================================================================== #

    # ------------------------------------------------------------------ #
    # MACD (12, 26, 9)
    # ------------------------------------------------------------------ #
    macd_val: float | None = None
    macd_signal_line_val: float | None = None
    macd_histogram_val: float | None = None
    macd_signal = "Neutral"

    if len(df) >= 35:
        try:
            ml, sl, hist = _macd(close)
            if pd.notna(ml.iloc[-1]):
                macd_val = round(float(ml.iloc[-1]), 4)
                macd_signal_line_val = round(float(sl.iloc[-1]), 4)
                hist_clean = hist.dropna()
                if len(hist_clean) >= 2:
                    curr_h = float(hist_clean.iloc[-1])
                    prev_h = float(hist_clean.iloc[-2])
                    macd_histogram_val = round(curr_h, 4)
                    if curr_h > 0 and prev_h <= 0:
                        macd_signal = "Bullish Crossover"
                    elif curr_h < 0 and prev_h >= 0:
                        macd_signal = "Bearish Crossover"
                    elif curr_h > 0 and curr_h > prev_h:
                        macd_signal = "Bullish Momentum"
                    elif curr_h < 0 and curr_h < prev_h:
                        macd_signal = "Bearish Momentum"
        except Exception as e:
            logger.debug(f"MACD computation failed: {e}")

    # ------------------------------------------------------------------ #
    # ADX (14)
    # ------------------------------------------------------------------ #
    adx_val: float | None = None
    adx_signal_str = "Neutral"

    if len(df) >= 28:
        try:
            adx_s, _, _ = _adx(high, low, close, 14)
            val = adx_s.iloc[-1]
            if pd.notna(val):
                adx_val = round(float(val), 2)
                if adx_val >= 25:
                    adx_signal_str = "Strong Trend (>25)"
                elif adx_val >= 20:
                    adx_signal_str = "Moderate Trend (20-25)"
                else:
                    adx_signal_str = "Weak/Ranging (<20)"
        except Exception as e:
            logger.debug(f"ADX computation failed: {e}")

    # ------------------------------------------------------------------ #
    # ATR (14)
    # ------------------------------------------------------------------ #
    atr_val: float | None = None

    if len(df) >= 15:
        try:
            atr_s = _atr(high, low, close, 14)
            val = atr_s.iloc[-1]
            if pd.notna(val):
                atr_val = round(float(val), 2)
        except Exception as e:
            logger.debug(f"ATR computation failed: {e}")

    # ------------------------------------------------------------------ #
    # Stochastic RSI (14, smooth_k=3)
    # ------------------------------------------------------------------ #
    stoch_rsi_k_val: float | None = None

    if len(df) >= 30:
        try:
            k_s = _stoch_rsi_k(close, 14, 3)
            val = k_s.iloc[-1]
            if pd.notna(val):
                stoch_rsi_k_val = round(float(val), 2)
        except Exception as e:
            logger.debug(f"StochRSI computation failed: {e}")

    # ------------------------------------------------------------------ #
    # OBV direction
    # ------------------------------------------------------------------ #
    obv_signal: str | None = None

    if volume is not None and len(df) >= 10:
        try:
            obv_s = _obv(close, volume)
            obv_recent = obv_s.dropna().tail(10)
            if len(obv_recent) >= 5:
                obv_slope = float(obv_recent.iloc[-1]) - float(obv_recent.iloc[0])
                obv_signal = "Bullish" if obv_slope > 0 else "Bearish"
        except Exception as e:
            logger.debug(f"OBV computation failed: {e}")

    # ------------------------------------------------------------------ #
    # Volume surge (today vs 20-day average)
    # ------------------------------------------------------------------ #
    volume_ratio: float | None = None
    volume_surge: bool | None = None

    if volume is not None and len(df) >= 22:
        try:
            today_vol = float(volume.iloc[-1])
            avg_vol = float(volume.iloc[-22:-1].mean())
            if avg_vol > 0:
                volume_ratio = round(today_vol / avg_vol, 2)
                volume_surge = volume_ratio >= 1.5
        except Exception as e:
            logger.debug(f"Volume analysis failed: {e}")

    return TechnicalData(
        current_price=round(current_price, 2),
        ema_50=ema_50,
        ema_200=ema_200,
        rsi_14=rsi_14,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        support_level=support_level,
        resistance_level=resistance_level,
        ema_signal=ema_signal,
        rsi_signal=rsi_signal,
        price_vs_ema200=price_vs_ema200,
        weekly_change_pct=weekly_change_pct,
        monthly_change_pct=monthly_change_pct,
        macd=macd_val,
        macd_signal_line=macd_signal_line_val,
        macd_histogram=macd_histogram_val,
        macd_signal=macd_signal,
        adx=adx_val,
        adx_signal=adx_signal_str,
        atr=atr_val,
        stoch_rsi_k=stoch_rsi_k_val,
        obv_signal=obv_signal,
        volume_ratio=volume_ratio,
        volume_surge=volume_surge,
    )


def _compute_pivot_levels(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    Classic Pivot Point support / resistance from the last 20 sessions.

    Pivot = (H + L + C) / 3
    S1    = 2 * Pivot - H
    R1    = 2 * Pivot - L
    """
    try:
        recent = df.tail(20)
        h = float(recent["High"].max())
        l = float(recent["Low"].min())
        c = float(recent["Close"].iloc[-1])
        pivot = (h + l + c) / 3
        return round(2 * pivot - h, 2), round(2 * pivot - l, 2)
    except Exception as e:
        logger.debug(f"Pivot computation failed: {e}")
        return None, None
