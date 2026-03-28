"""
Outils d'optimisation/trading d'un portefeuille simulé type PEA via yfinance.

Le toolkit expose :
- `generate_pea_trading_plan` : sélection automatique de titres PEA-like,
  prise en compte de l'actualité (news yfinance + contexte fourni), optimisation,
  et génération d'ordres simulés achat/vente avec coûts de transaction.
- `optimize_pea_portfolio` : compatibilité avec l'ancien flux (allocation initiale).
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from agno.tools import Toolkit, tool

logger = logging.getLogger(__name__)
PORTFOLIO_STATE_DIR = Path(__file__).resolve().parents[2] / "data" / "pea_portfolios"

# Liste indicative (non exhaustive) de suffixes européens souvent compatibles PEA.
# Vérification heuristique : ne remplace pas une vérification réglementaire.
PEA_LIKE_SUFFIXES = {
    ".PA", ".AS", ".BR", ".LS", ".MI", ".DE", ".MC", ".HE",
    ".ST", ".CO", ".OL", ".VI", ".IR", ".WA", ".AT", ".TL", ".RG",
}

# Univers par défaut (tickers yfinance) à dominante actions/ETF européens.
# L'agent peut surcharger cet univers via `candidate_tickers`.
DEFAULT_PEA_UNIVERSE = [
    # France
    "MC.PA", "OR.PA", "AIR.PA", "AI.PA", "BNP.PA", "SAN.PA", "SU.PA", "TTE.PA",
    "CAP.PA", "DG.PA", "ACA.PA", "GLE.PA", "VIE.PA", "RMS.PA", "DSY.PA", "RI.PA",
    "HO.PA", "ENGI.PA", "EN.PA", "EL.PA", "URW.PA", "STLAP.PA", "WLN.PA", "KER.PA",
    # ETF souvent utilisés en PEA (à vérifier selon broker)
    "CW8.PA", "EWLD.PA", "PAEEM.PA",
    # Pays-Bas
    "ASML.AS", "INGA.AS", "PHIA.AS", "AD.AS", "HEIA.AS", "KPN.AS",
    # Allemagne
    "SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BMW.DE", "VOW3.DE", "DTE.DE", "ADS.DE", "MUV2.DE", "DB1.DE",
    # Espagne
    "IBE.MC", "SAN.MC", "ITX.MC",
    # Italie
    "ENI.MI", "ISP.MI", "UCG.MI", "ENEL.MI",
]

RISK_PROFILES = {
    "prudent": 1.20,
    "equilibre": 0.70,
    "dynamique": 0.35,
    "offensif": 0.15,
}

PROFILE_SCORING = {
    "prudent": {"momentum_mult": 0.85, "vol_penalty": 1.10},
    "equilibre": {"momentum_mult": 1.00, "vol_penalty": 0.85},
    "dynamique": {"momentum_mult": 1.15, "vol_penalty": 0.60},
    "offensif": {"momentum_mult": 1.30, "vol_penalty": 0.40},
}

PROFILE_STRATEGY_WEIGHTS = {
    "prudent": {
        "trend_following": 0.28,
        "momentum_cross_sectional": 0.14,
        "mean_reversion": 0.10,
        "breakout": 0.08,
        "quality_risk_control": 0.40,
    },
    "equilibre": {
        "trend_following": 0.27,
        "momentum_cross_sectional": 0.22,
        "mean_reversion": 0.10,
        "breakout": 0.11,
        "quality_risk_control": 0.30,
    },
    "dynamique": {
        "trend_following": 0.23,
        "momentum_cross_sectional": 0.29,
        "mean_reversion": 0.10,
        "breakout": 0.20,
        "quality_risk_control": 0.18,
    },
    "offensif": {
        "trend_following": 0.18,
        "momentum_cross_sectional": 0.31,
        "mean_reversion": 0.10,
        "breakout": 0.29,
        "quality_risk_control": 0.12,
    },
}

POSITIVE_WORDS = {
    "hausse", "croissance", "record", "surperformance", "upgrade", "releve", "beat",
    "benefice", "contrat", "acquisition", "solide", "rebond", "acceleration", "optimiste",
}
NEGATIVE_WORDS = {
    "baisse", "warning", "downgrade", "abaisse", "perte", "retard", "amende", "litige",
    "cession", "defavorable", "recession", "faible", "ralentissement", "risque", "pression",
}


def _fmt(value: Any, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def _series_top(series: pd.Series, top_n: int = 6) -> List[Tuple[str, float]]:
    if series is None or series.empty:
        return []
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return []
    top = clean.sort_values(ascending=False).head(max(1, int(top_n)))
    return [(str(idx), float(val)) for idx, val in top.items()]


def _sanitize_portfolio_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return "default_pea_portfolio"
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    safe = safe.strip("._-")
    return safe or "default_pea_portfolio"


def _resolve_portfolio_state_path(portfolio_id: str, custom_path: str) -> Path:
    if custom_path and str(custom_path).strip():
        p = Path(str(custom_path).strip()).expanduser()
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p
        return p
    safe_id = _sanitize_portfolio_id(portfolio_id)
    return PORTFOLIO_STATE_DIR / f"{safe_id}.json"


def _normalize_positions_mapping(raw_positions: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not isinstance(raw_positions, dict):
        return out
    for key, value in raw_positions.items():
        ticker = str(key).strip().upper()
        if not ticker:
            continue
        try:
            qty = int(float(value))
        except Exception:
            continue
        if qty > 0:
            out[ticker] = qty
    return out


def _load_portfolio_state(path: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        if not path.exists():
            return None, None
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return None, None
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return None, "Format d'état portefeuille invalide (objet JSON attendu)."
        return payload, None
    except Exception as e:
        return None, f"Impossible de lire l'état portefeuille: {e}"


def _save_portfolio_state(path: Path, payload: Dict[str, Any]) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return None
    except Exception as e:
        return f"Impossible d'écrire l'état portefeuille: {e}"


def _has_explicit_positions_input(raw_positions: Any) -> bool:
    text = str(raw_positions or "").strip()
    if not text:
        return False
    lowered = text.lower()
    return lowered not in {"[]", "{}", "null", "none"}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "oui", "y"}


def _parse_tickers(raw_tickers: str) -> List[str]:
    if not raw_tickers:
        return []
    tickers: List[str] = []
    for chunk in raw_tickers.replace("\n", ",").split(","):
        ticker = chunk.strip().upper()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers


def _parse_positions(raw_positions: str) -> Tuple[Dict[str, int], List[str]]:
    """
    Parse un portefeuille courant depuis JSON.

    Formats acceptés:
    - [{"ticker":"MC.PA","shares":10}, ...]
    - {"MC.PA": 10, "AIR.PA": 5}
    - lignes `TICKER:QUANTITE`
    """
    warnings: List[str] = []
    if not raw_positions or not str(raw_positions).strip():
        return {}, warnings

    text = str(raw_positions).strip()
    positions: Dict[str, int] = {}

    def _add(ticker: str, qty: Any) -> None:
        t = str(ticker).strip().upper()
        if not t:
            return
        try:
            q = int(float(qty))
        except Exception:
            warnings.append(f"Position ignorée pour {t}: quantité invalide ({qty}).")
            return
        if q <= 0:
            return
        positions[t] = positions.get(t, 0) + q

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for ticker, qty in parsed.items():
                _add(ticker, qty)
            return positions, warnings
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    ticker = item.get("ticker") or item.get("symbol")
                    qty = item.get("shares")
                    if qty is None:
                        qty = item.get("quantity")
                    _add(ticker, qty)
            return positions, warnings
    except Exception:
        # fallback format texte multi-lignes
        pass

    for line in text.splitlines():
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        _add(left, right)

    return positions, warnings


def _filter_pea_like_tickers(tickers: List[str]) -> Tuple[List[str], List[str], List[str]]:
    accepted: List[str] = []
    rejected: List[str] = []
    warnings: List[str] = []

    for ticker in tickers:
        if "." not in ticker:
            rejected.append(ticker)
            warnings.append(
                f"{ticker}: suffixe de place manquant (ex: .PA). Compatibilité PEA non vérifiable."
            )
            continue
        suffix = "." + ticker.split(".")[-1]
        if suffix in PEA_LIKE_SUFFIXES:
            accepted.append(ticker)
        else:
            rejected.append(ticker)
            warnings.append(f"{ticker}: suffixe {suffix} hors univers PEA-like configuré.")

    return accepted, rejected, warnings


def _extract_field(raw: pd.DataFrame, field: str, tickers: List[str]) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        if field not in level0:
            return pd.DataFrame()
        frame = raw[field].copy()
        cols = [c for c in frame.columns if c in tickers]
        if cols:
            frame = frame[cols]
        return frame

    if field not in raw.columns:
        return pd.DataFrame()

    col_name = tickers[0] if tickers else "ASSET"
    frame = raw[[field]].copy()
    frame.columns = [col_name]
    return frame


def _zscore_series(series: pd.Series) -> pd.Series:
    s = series.astype(float).replace([np.inf, -np.inf], np.nan)
    mean = float(s.mean()) if not s.empty else 0.0
    std = float(s.std()) if not s.empty else 0.0
    if std <= 1e-12:
        return pd.Series(0.0, index=series.index)
    return (s - mean) / std


def _momentum(close: pd.DataFrame, window: int) -> pd.Series:
    if close.empty or len(close) < 2:
        return pd.Series(0.0, index=close.columns)
    w = min(window, len(close) - 1)
    if w <= 0:
        return pd.Series(0.0, index=close.columns)
    return close.iloc[-1] / close.iloc[-(w + 1)] - 1.0


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1.0
    return float(drawdown.min())


def _safe_last(series: pd.Series, default: float = 0.0) -> float:
    if series is None or series.empty:
        return float(default)
    clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float(default)
    return float(clean.iloc[-1])


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=max(2, min(span, 6))).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.clip(0.0, 100.0)


def _macd(series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(series, 12)
    ema_slow = _ema(series, 26)
    macd_line = ema_fast - ema_slow
    signal = _ema(macd_line, 9)
    hist = macd_line - signal
    return macd_line, signal, hist


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=close.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=close.index,
    )

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean() / atr.replace(0.0, np.nan)
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan) * 100.0
    return dx.ewm(alpha=1.0 / max(period, 1), adjust=False, min_periods=period).mean()


def _bollinger(close: pd.Series, period: int = 20, nb_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(period, min_periods=max(5, period // 2)).mean()
    std = close.rolling(period, min_periods=max(5, period // 2)).std(ddof=0)
    upper = mid + nb_std * std
    lower = mid - nb_std * std
    return mid, upper, lower


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    lowest = low.rolling(period, min_periods=max(5, period // 2)).min()
    highest = high.rolling(period, min_periods=max(5, period // 2)).max()
    k = 100.0 * (close - lowest) / (highest - lowest).replace(0.0, np.nan)
    d = k.rolling(3, min_periods=2).mean()
    return k, d


def _candlestick_pattern_signal(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    body = (close - open_).abs()
    candle_range = (high - low).replace(0.0, np.nan)
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low

    prev_open = open_.shift(1)
    prev_close = close.shift(1)

    bullish_engulfing = (
        (close > open_)
        & (prev_close < prev_open)
        & (close >= prev_open)
        & (open_ <= prev_close)
    )
    bearish_engulfing = (
        (close < open_)
        & (prev_close > prev_open)
        & (close <= prev_open)
        & (open_ >= prev_close)
    )
    hammer = (lower_wick > body * 2.2) & (upper_wick <= body * 1.2)
    shooting_star = (upper_wick > body * 2.2) & (lower_wick <= body * 1.2)
    doji = body <= candle_range * 0.1

    signal = (
        bullish_engulfing.astype(float)
        + hammer.astype(float) * 0.8
        - bearish_engulfing.astype(float)
        - shooting_star.astype(float) * 0.8
    )
    signal = signal.where(~doji, 0.0)
    return signal


def _compute_ta_features(
    close: pd.DataFrame,
    open_prices: pd.DataFrame,
    high_prices: pd.DataFrame,
    low_prices: pd.DataFrame,
    volume: pd.DataFrame,
) -> Dict[str, pd.Series]:
    tickers = list(close.columns)
    raw: Dict[str, Dict[str, float]] = {
        "sma50_above_sma200": {},
        "trend_distance": {},
        "rsi14": {},
        "macd_line": {},
        "macd_signal": {},
        "macd_hist": {},
        "atr_pct": {},
        "adx14": {},
        "bb_pos": {},
        "bb_width": {},
        "stoch_k": {},
        "stoch_d": {},
        "breakout20": {},
        "breakdown20": {},
        "volume_ratio20": {},
        "roc20": {},
        "pattern_signal": {},
    }

    for ticker in tickers:
        c = pd.to_numeric(close[ticker], errors="coerce").dropna()
        if c.empty:
            continue
        idx = c.index

        o = pd.to_numeric(open_prices[ticker].reindex(idx), errors="coerce").ffill().bfill().fillna(c)
        h = pd.to_numeric(high_prices[ticker].reindex(idx), errors="coerce").ffill().bfill().fillna(c)
        l = pd.to_numeric(low_prices[ticker].reindex(idx), errors="coerce").ffill().bfill().fillna(c)
        v = pd.to_numeric(volume[ticker].reindex(idx), errors="coerce").fillna(0.0)

        sma50 = c.rolling(50, min_periods=20).mean()
        sma200 = c.rolling(200, min_periods=60).mean()
        rsi14 = _rsi(c, period=14)
        macd_line, macd_signal, macd_hist = _macd(c)
        atr14 = _atr(h, l, c, period=14)
        adx14 = _adx(h, l, c, period=14)
        bb_mid, bb_upper, bb_lower = _bollinger(c, period=20, nb_std=2.0)
        stoch_k, stoch_d = _stochastic(h, l, c, period=14)
        pattern_signal = _candlestick_pattern_signal(o, h, l, c)

        roll_max20 = c.rolling(20, min_periods=10).max()
        roll_min20 = c.rolling(20, min_periods=10).min()
        vol_avg20 = v.rolling(20, min_periods=10).mean()
        roc20 = c.pct_change(20)

        sma50_last = _safe_last(sma50, _safe_last(c, 1.0))
        sma200_last = _safe_last(sma200, sma50_last)
        close_last = _safe_last(c, 0.0)
        bb_upper_last = _safe_last(bb_upper, close_last)
        bb_lower_last = _safe_last(bb_lower, close_last)
        bb_mid_last = _safe_last(bb_mid, close_last)
        atr_last = _safe_last(atr14, 0.0)
        vol_avg_last = _safe_last(vol_avg20, 0.0)
        vol_last = _safe_last(v, 0.0)

        raw["sma50_above_sma200"][ticker] = 1.0 if sma50_last >= sma200_last else -1.0
        raw["trend_distance"][ticker] = (close_last / max(sma50_last, 1e-9)) - 1.0
        raw["rsi14"][ticker] = _safe_last(rsi14, 50.0)
        raw["macd_line"][ticker] = _safe_last(macd_line, 0.0)
        raw["macd_signal"][ticker] = _safe_last(macd_signal, 0.0)
        raw["macd_hist"][ticker] = _safe_last(macd_hist, 0.0)
        raw["atr_pct"][ticker] = atr_last / max(close_last, 1e-9)
        raw["adx14"][ticker] = _safe_last(adx14, 20.0)
        raw["bb_pos"][ticker] = (close_last - bb_lower_last) / max(bb_upper_last - bb_lower_last, 1e-9)
        raw["bb_width"][ticker] = (bb_upper_last - bb_lower_last) / max(bb_mid_last, 1e-9)
        raw["stoch_k"][ticker] = _safe_last(stoch_k, 50.0)
        raw["stoch_d"][ticker] = _safe_last(stoch_d, 50.0)
        raw["breakout20"][ticker] = close_last / max(_safe_last(roll_max20, close_last), 1e-9) - 1.0
        raw["breakdown20"][ticker] = close_last / max(_safe_last(roll_min20, close_last), 1e-9) - 1.0
        raw["volume_ratio20"][ticker] = vol_last / max(vol_avg_last, 1e-9)
        raw["roc20"][ticker] = _safe_last(roc20, 0.0)
        raw["pattern_signal"][ticker] = _safe_last(pattern_signal, 0.0)

    defaults = {
        "sma50_above_sma200": 0.0,
        "trend_distance": 0.0,
        "rsi14": 50.0,
        "macd_line": 0.0,
        "macd_signal": 0.0,
        "macd_hist": 0.0,
        "atr_pct": 0.0,
        "adx14": 20.0,
        "bb_pos": 0.5,
        "bb_width": 0.0,
        "stoch_k": 50.0,
        "stoch_d": 50.0,
        "breakout20": 0.0,
        "breakdown20": 0.0,
        "volume_ratio20": 1.0,
        "roc20": 0.0,
        "pattern_signal": 0.0,
    }

    out: Dict[str, pd.Series] = {}
    for name, values in raw.items():
        s = pd.Series(values, dtype=float).reindex(tickers)
        out[name] = s.replace([np.inf, -np.inf], np.nan).fillna(defaults.get(name, 0.0))
    return out


def _project_weights(weights: np.ndarray, max_weight: float) -> np.ndarray:
    if weights.size == 0:
        return weights
    w = np.maximum(weights.astype(float), 0.0)
    total = float(np.sum(w))
    if total <= 0:
        w = np.ones_like(w) / len(w)
    else:
        w = w / total

    if max_weight >= 0.999:
        return w

    for _ in range(30):
        over = w > max_weight
        if not np.any(over):
            break
        excess = float(np.sum(w[over] - max_weight))
        w[over] = max_weight

        under = ~over
        if not np.any(under):
            break
        room = np.maximum(max_weight - w[under], 0.0)
        room_sum = float(np.sum(room))
        if room_sum <= 1e-12:
            w[under] += excess / max(float(np.sum(under)), 1.0)
        else:
            w[under] += excess * (room / room_sum)

        w = np.maximum(w, 0.0)
        total = float(np.sum(w))
        if total <= 0:
            w = np.ones_like(w) / len(w)
        else:
            w = w / total

    w = np.maximum(w, 0.0)
    total = float(np.sum(w))
    if total <= 0:
        w = np.ones_like(w) / len(w)
    else:
        w = w / total
    return w


def _optimize_weights(
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    risk_aversion: float,
    max_weight: float,
) -> Tuple[np.ndarray, float, float]:
    n_assets = len(expected_returns)
    if n_assets == 0:
        return np.array([]), 0.0, 0.0

    if n_assets == 1:
        w = np.array([1.0])
        ann_return = float(expected_returns[0])
        ann_vol = float(np.sqrt(max(float(covariance[0, 0]), 1e-12)))
        return w, ann_return, ann_vol

    if max_weight * n_assets < 0.999:
        max_weight = min(1.0, 1.0 / n_assets + 1e-6)

    cov = np.nan_to_num(covariance.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    cov += np.eye(n_assets) * 1e-9
    mu = np.nan_to_num(expected_returns.astype(float), nan=0.0, posinf=0.0, neginf=0.0)

    rng = np.random.default_rng(42)
    best_w = np.ones(n_assets) / n_assets
    best_score = -1e18
    best_ret = 0.0
    best_vol = 0.0

    def evaluate(w: np.ndarray) -> Tuple[float, float, float]:
        ann_return = float(np.dot(mu, w))
        variance = float(np.dot(w, cov @ w))
        ann_vol = float(np.sqrt(max(variance, 1e-12)))
        score = ann_return - risk_aversion * ann_vol
        return score, ann_return, ann_vol

    for attempt in range(50):
        if attempt == 0:
            w = np.ones(n_assets) / n_assets
        else:
            w = rng.dirichlet(np.ones(n_assets))
        w = _project_weights(w, max_weight=max_weight)

        step = 0.12
        for _ in range(260):
            _, _, vol = evaluate(w)
            grad = mu - risk_aversion * ((cov @ w) / max(vol, 1e-9))
            w = _project_weights(w + step * grad, max_weight=max_weight)
            step *= 0.995

        score, ann_ret, ann_vol = evaluate(w)
        if score > best_score:
            best_score = score
            best_w = w.copy()
            best_ret = ann_ret
            best_vol = ann_vol

    return best_w, best_ret, best_vol


def _text_sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    tokens = [tok.strip(" .,;:!?()[]{}\"'").lower() for tok in text.split()]
    if not tokens:
        return 0.0
    pos = sum(1 for tok in tokens if tok in POSITIVE_WORDS)
    neg = sum(1 for tok in tokens if tok in NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    score = (pos - neg) / total
    return float(np.clip(score, -1.0, 1.0))


def _context_signal_for_ticker(ticker: str, context: str) -> float:
    if not context:
        return 0.0
    text_up = context.upper()
    base = ticker.split(".")[0].upper()
    if ticker.upper() in text_up or base in text_up:
        return _text_sentiment_score(context)
    return 0.0


def _yfinance_news_signal(ticker: str, max_items: int = 8) -> Tuple[float, List[str]]:
    try:
        obj = yf.Ticker(ticker)
        items = getattr(obj, "news", None) or []
    except Exception:
        return 0.0, []

    signals: List[float] = []
    headlines: List[str] = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        combined = f"{title} {summary}".strip()
        if not combined:
            continue
        score = _text_sentiment_score(combined)
        if score != 0.0:
            signals.append(score)
        if title:
            headlines.append(title)

    if not signals:
        return 0.0, headlines[:3]
    return float(np.clip(float(np.mean(signals)), -1.0, 1.0)), headlines[:3]


def _estimate_broker_fee(
    amount_eur: float,
    side: str,
    fee_profile: str,
    custom_fee_rate_pct: float,
    custom_min_fee_eur: float,
    custom_fee_cap_pct: float,
) -> float:
    amount = max(float(amount_eur), 0.0)
    if amount <= 0:
        return 0.0

    profile = (fee_profile or "credit_agricole_investore_integral").strip().lower()
    if profile == "credit_agricole_investore_integral":
        # Approximation barème Invest Store Intégral (à vérifier dans la tarification du contrat).
        # Modèle: paliers sur petits ordres puis pourcentage sur ordres plus élevés.
        if amount <= 500:
            return 0.99
        if amount <= 1000:
            return 1.90
        if amount <= 2000:
            return 2.90
        return max(0.99, amount * 0.0009)

    # Mode custom
    rate = max(float(custom_fee_rate_pct), 0.0) / 100.0
    min_fee = max(float(custom_min_fee_eur), 0.0)
    fee = max(min_fee, amount * rate)
    cap_pct = max(float(custom_fee_cap_pct), 0.0)
    if cap_pct > 0:
        fee = min(fee, amount * (cap_pct / 100.0))
    return float(fee)


def _calc_order_costs(
    side: str,
    ticker: str,
    gross_amount_eur: float,
    fee_profile: str,
    custom_fee_rate_pct: float,
    custom_min_fee_eur: float,
    custom_fee_cap_pct: float,
    slippage_pct: float,
    french_ftt_buy_pct: float,
) -> Dict[str, float]:
    gross = max(float(gross_amount_eur), 0.0)
    fee = _estimate_broker_fee(
        amount_eur=gross,
        side=side,
        fee_profile=fee_profile,
        custom_fee_rate_pct=custom_fee_rate_pct,
        custom_min_fee_eur=custom_min_fee_eur,
        custom_fee_cap_pct=custom_fee_cap_pct,
    )
    slippage = gross * max(float(slippage_pct), 0.0) / 100.0

    ftt = 0.0
    if side.lower() == "buy" and ticker.endswith(".PA") and french_ftt_buy_pct > 0:
        ftt = gross * french_ftt_buy_pct / 100.0

    if side.lower() == "buy":
        net_cash_impact = -(gross + fee + slippage + ftt)
    else:
        net_cash_impact = gross - fee - slippage

    return {
        "gross_amount_eur": float(gross),
        "broker_fee_eur": float(fee),
        "slippage_eur": float(slippage),
        "ftt_eur": float(ftt),
        "net_cash_impact_eur": float(net_cash_impact),
    }


class PEAPortfolioTools(Toolkit):
    """Toolkit Agno pour sélection/optimisation/trading simulé PEA."""

    def __init__(self, **kwargs):
        super().__init__(
            name="pea_portfolio_tools",
            tools=[self.generate_pea_trading_plan, self.optimize_pea_portfolio],
            **kwargs,
        )

    @tool(
        description=(
            "Sélectionne automatiquement des titres PEA-like, optimise une allocation et génère des ordres "
            "simulés achat/vente avec coûts (profil Crédit Agricole configurable) en tenant compte de l'actualité."
        )
    )
    def generate_pea_trading_plan(
        self,
        available_cash_eur: float | None = None,
        available_cash: float | None = None,
        current_positions_json: str = "[]",
        current_positions: str = "",
        candidate_tickers: str = "",
        risk_profile: str = "equilibre",
        lookback_years: int = 3,
        lookback_period: int | None = None,
        max_positions: int = 8,
        max_weight_pct: float = 25.0,
        news_weight_pct: float = 20.0,
        news_context: str = "",
        use_yfinance_news: bool = True,
        broker_fee_profile: str = "credit_agricole_investore_integral",
        custom_fee_rate_pct: float = 0.09,
        custom_min_fee_eur: float = 0.99,
        custom_fee_cap_pct: float = 0.50,
        estimated_slippage_pct: float = 0.03,
        french_ftt_buy_pct: float = 0.0,
        portfolio_id: str = "default_pea_portfolio",
        persist_portfolio_state: bool = False,
        portfolio_state_file: str = "",
        force_reset_portfolio_state: bool = False,
        max_saved_runs: int = 500,
    ) -> str:
        """
        Génère un plan de trading simulé (achat/vente) orienté performance avec coûts de transaction.

        Args:
            available_cash_eur: Trésorerie disponible en EUR.
            available_cash: Alias rétro-compatible de available_cash_eur.
            current_positions_json: Portefeuille courant en JSON.
            current_positions: Alias rétro-compatible de current_positions_json.
            candidate_tickers: Univers candidat (liste de tickers yfinance), vide => univers par défaut.
            risk_profile: prudent | equilibre | dynamique | offensif.
            lookback_years: Fenêtre historique (années).
            lookback_period: Alias rétro-compatible de lookback_years.
            max_positions: Nombre maximum de lignes en portefeuille cible.
            max_weight_pct: Poids maximum par ligne.
            news_weight_pct: Pondération de l'actualité dans le score (0-80%).
            news_context: Contexte d'actualité fourni par l'agent (résumé web_search/search_news).
            use_yfinance_news: Utiliser aussi les headlines yfinance ticker par ticker.
            broker_fee_profile: credit_agricole_investore_integral | custom.
            custom_fee_rate_pct: Frais proportionnels custom (%).
            custom_min_fee_eur: Minimum par ordre custom.
            custom_fee_cap_pct: Plafond custom (% du nominal), 0 pour désactiver.
            estimated_slippage_pct: Slippage estimé (% du nominal).
            french_ftt_buy_pct: Taxe FTT appliquée aux achats .PA (optionnel, ex 0.3).
            portfolio_id: Identifiant du portefeuille simulé suivi dans le temps.
            persist_portfolio_state: Si true, sauvegarde/relit l'état du portefeuille entre runs.
            portfolio_state_file: Chemin JSON custom d'état (optionnel).
            force_reset_portfolio_state: Si true, ignore l'état existant (redémarrage simulation).
            max_saved_runs: Nombre maximum d'exécutions conservées dans l'historique.

        Returns:
            JSON string avec sélection, allocation cible, ordres et métriques nettes des coûts.
        """
        try:
            warnings: List[str] = []
            if available_cash_eur is None and available_cash is not None:
                available_cash_eur = available_cash
            if available_cash_eur is None:
                return json.dumps(
                    {
                        "error": "Paramètre cash manquant: fournir `available_cash_eur` (ou alias `available_cash`)."
                    },
                    ensure_ascii=False,
                )
            if current_positions_json in {"", "[]", "{}"} and current_positions:
                current_positions_json = current_positions
            if lookback_period is not None:
                lookback_years = lookback_period

            # Alias de profils anglais -> profils internes
            rp_alias = {
                "dynamic": "dynamique",
                "balanced": "equilibre",
                "aggressive": "offensif",
                "conservative": "prudent",
                "moderate": "equilibre",
            }
            risk_profile = rp_alias.get(str(risk_profile).strip().lower(), risk_profile)

            logger.info(
                "[PEA][Plan] Début génération | cash=%s EUR | risk_profile=%s | lookback=%sy | max_positions=%s | max_weight_pct=%s | news_weight_pct=%s",
                _fmt(available_cash_eur, 2),
                risk_profile,
                lookback_years,
                max_positions,
                _fmt(max_weight_pct, 2),
                _fmt(news_weight_pct, 2),
            )

            cash = float(available_cash_eur)
            if cash < 0:
                return json.dumps({"error": "`available_cash_eur` doit être >= 0."}, ensure_ascii=False)

            persistence_enabled = _as_bool(persist_portfolio_state)
            force_reset_state = _as_bool(force_reset_portfolio_state)
            portfolio_id_safe = _sanitize_portfolio_id(portfolio_id)
            state_path = _resolve_portfolio_state_path(portfolio_id_safe, portfolio_state_file)
            loaded_state_payload: Dict[str, Any] | None = None
            loaded_state_used = False

            if persistence_enabled and not force_reset_state:
                loaded_state_payload, load_err = _load_portfolio_state(state_path)
                if load_err:
                    warnings.append(load_err)
                elif loaded_state_payload:
                    logger.info(
                        "[PEA][Tracking] État portefeuille trouvé: %s",
                        str(state_path),
                    )

            risk_profile_key = (risk_profile or "equilibre").strip().lower()
            if risk_profile_key not in RISK_PROFILES:
                risk_profile_key = "equilibre"
                warnings.append("Profil de risque inconnu: fallback sur `equilibre`.")

            lookback_years = int(max(1, min(int(lookback_years), 10)))
            max_positions = int(max(1, min(int(max_positions), 20)))
            max_weight_pct = float(max(5.0, min(float(max_weight_pct), 100.0)))
            news_weight_pct = float(max(0.0, min(float(news_weight_pct), 80.0)))
            news_weight = news_weight_pct / 100.0
            slippage_pct = float(max(0.0, min(float(estimated_slippage_pct), 2.0)))
            ftt_pct = float(max(0.0, min(float(french_ftt_buy_pct), 2.0)))
            max_saved_runs = int(max(10, min(int(max_saved_runs), 2000)))

            # Portfolio courant
            if loaded_state_payload and not _has_explicit_positions_input(current_positions_json):
                state_obj = loaded_state_payload.get("state", {}) if isinstance(loaded_state_payload, dict) else {}
                current_positions = _normalize_positions_mapping(state_obj.get("positions", {}))
                try:
                    cash = float(state_obj.get("cash_eur", cash))
                except Exception:
                    warnings.append("Cash persistant invalide: fallback sur available_cash_eur.")
                loaded_state_used = True
                warnings.append(
                    "État portefeuille persistant chargé (cash/positions du dernier run)."
                )
            else:
                current_positions, pos_warnings = _parse_positions(current_positions_json)
                warnings.extend(pos_warnings)
                if loaded_state_payload and _has_explicit_positions_input(current_positions_json):
                    warnings.append(
                        "État portefeuille persistant ignoré: positions explicites fournies dans la requête."
                    )

            held_tickers = list(current_positions.keys())
            logger.info(
                "[PEA][Inputs] Positions courantes: %s ligne(s) | tickers=%s",
                len(current_positions),
                held_tickers[:12],
            )
            logger.info(
                "[PEA][Tracking] persistence_enabled=%s | loaded_state_used=%s | state_file=%s",
                persistence_enabled,
                loaded_state_used,
                str(state_path),
            )

            # Univers candidat
            requested_tickers = _parse_tickers(candidate_tickers)
            if not requested_tickers:
                requested_tickers = list(DEFAULT_PEA_UNIVERSE)
                warnings.append("Aucun ticker fourni: utilisation de l'univers PEA-like par défaut.")
            logger.info(
                "[PEA][Inputs] Univers candidat demandé: %s tickers",
                len(requested_tickers),
            )

            combined_tickers = list(dict.fromkeys(requested_tickers + held_tickers))
            pea_tickers, rejected_tickers, filter_warnings = _filter_pea_like_tickers(combined_tickers)
            warnings.extend(filter_warnings)
            logger.info(
                "[PEA][Universe] Tickers combinés=%s | PEA-like retenus=%s | rejetés=%s",
                len(combined_tickers),
                len(pea_tickers),
                len(rejected_tickers),
            )
            if rejected_tickers:
                logger.info("[PEA][Universe] Rejets (extrait): %s", rejected_tickers[:12])

            if not pea_tickers:
                return json.dumps(
                    {
                        "error": "Aucun ticker éligible PEA-like dans l'univers fourni.",
                        "rejected_tickers": rejected_tickers,
                        "warnings": warnings,
                    },
                    ensure_ascii=False,
                )

            raw = yf.download(
                tickers=pea_tickers,
                period=f"{lookback_years}y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            logger.info(
                "[PEA][Data] Téléchargement yfinance terminé | tickers=%s | lookback=%sy",
                len(pea_tickers),
                lookback_years,
            )
            close = _extract_field(raw, "Close", pea_tickers)
            if close.empty:
                close = _extract_field(raw, "Adj Close", pea_tickers)
            open_prices = _extract_field(raw, "Open", pea_tickers)
            high_prices = _extract_field(raw, "High", pea_tickers)
            low_prices = _extract_field(raw, "Low", pea_tickers)
            volume = _extract_field(raw, "Volume", pea_tickers)

            if close.empty:
                return json.dumps(
                    {
                        "error": "Impossible de récupérer les historiques de prix via yfinance.",
                        "tickers_used": pea_tickers,
                        "warnings": warnings,
                    },
                    ensure_ascii=False,
                )

            close = close.apply(pd.to_numeric, errors="coerce")
            close = close.dropna(how="all")
            if close.empty:
                return json.dumps({"error": "Historique prix vide après nettoyage."}, ensure_ascii=False)

            if open_prices.empty:
                open_prices = close.copy()
            else:
                open_prices = open_prices.apply(pd.to_numeric, errors="coerce")
            if high_prices.empty:
                high_prices = close.copy()
            else:
                high_prices = high_prices.apply(pd.to_numeric, errors="coerce")
            if low_prices.empty:
                low_prices = close.copy()
            else:
                low_prices = low_prices.apply(pd.to_numeric, errors="coerce")
            if volume.empty:
                volume = pd.DataFrame(0.0, index=close.index, columns=close.columns)
            else:
                volume = volume.apply(pd.to_numeric, errors="coerce")

            logger.info(
                "[PEA][Data] Historique brut | dates=%s | colonnes=%s",
                len(close.index),
                len(close.columns),
            )

            # Filtrage qualité données
            min_obs = max(90, int(len(close) * 0.60))
            valid_cols = [col for col in close.columns if int(close[col].notna().sum()) >= min_obs]
            close = close[valid_cols].ffill().dropna()
            open_prices = open_prices[valid_cols].ffill().bfill().reindex(close.index).fillna(close)
            high_prices = high_prices[valid_cols].ffill().bfill().reindex(close.index).fillna(close)
            low_prices = low_prices[valid_cols].ffill().bfill().reindex(close.index).fillna(close)
            volume = volume[valid_cols].reindex(close.index).fillna(0.0)

            if close.empty or len(close) < 90:
                return json.dumps(
                    {
                        "error": "Historique insuffisant (minimum 90 observations exploitables).",
                        "warnings": warnings,
                    },
                    ensure_ascii=False,
                )

            returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="all").fillna(0.0)
            if returns.empty:
                return json.dumps({"error": "Impossible de calculer les rendements."}, ensure_ascii=False)
            logger.info(
                "[PEA][Data] Historique exploitable | tickers valides=%s | observations=%s",
                len(close.columns),
                len(close.index),
            )

            # Tickers effectivement tradables (prix disponibles au dernier point)
            last_prices = close.iloc[-1].dropna()
            tradable_tickers = [t for t in close.columns if t in last_prices.index]
            if not tradable_tickers:
                return json.dumps({"error": "Aucun ticker tradable après nettoyage des prix."}, ensure_ascii=False)

            close = close[tradable_tickers]
            returns = returns[tradable_tickers]
            open_prices = open_prices[tradable_tickers]
            high_prices = high_prices[tradable_tickers]
            low_prices = low_prices[tradable_tickers]
            volume = volume[tradable_tickers]

            # Valorisation portefeuille avant
            unavailable_held = [t for t in held_tickers if t not in tradable_tickers]
            if unavailable_held:
                warnings.append(
                    "Tickers en portefeuille sans prix disponible (ignorés pour ce cycle): "
                    + ", ".join(unavailable_held)
                )

            current_values: Dict[str, float] = {}
            for ticker, shares in current_positions.items():
                if ticker in last_prices.index:
                    current_values[ticker] = float(shares) * float(last_prices[ticker])

            positions_value_before = float(sum(current_values.values()))
            portfolio_value_before = cash + positions_value_before
            if portfolio_value_before <= 0:
                return json.dumps(
                    {"error": "Capital total nul. Fournir du cash ou des positions valorisables."},
                    ensure_ascii=False,
                )
            cash_before_rebalance = float(cash)
            logger.info(
                "[PEA][Capital] Avant optimisation | cash=%s | positions=%s | total=%s",
                _fmt(cash, 2),
                _fmt(positions_value_before, 2),
                _fmt(portfolio_value_before, 2),
            )

            # Scoring technique
            mom_21 = _momentum(close, 21)
            mom_63 = _momentum(close, 63)
            mom_126 = _momentum(close, 126)
            ann_return = returns.mean() * 252.0
            ann_vol = returns.std() * np.sqrt(252.0)
            asset_mdd = returns.apply(_max_drawdown)

            if not volume.empty:
                euro_volume = (close * volume).tail(min(60, len(close))).mean()
            else:
                euro_volume = pd.Series(0.0, index=close.columns)

            ta_features = _compute_ta_features(
                close=close,
                open_prices=open_prices,
                high_prices=high_prices,
                low_prices=low_prices,
                volume=volume,
            )

            params = PROFILE_SCORING[risk_profile_key]
            momentum_mult = float(params["momentum_mult"])
            vol_penalty = float(params["vol_penalty"])
            strategy_weights = PROFILE_STRATEGY_WEIGHTS[risk_profile_key]

            z_m21 = _zscore_series(mom_21)
            z_m63 = _zscore_series(mom_63)
            z_m126 = _zscore_series(mom_126)
            z_ann_return = _zscore_series(ann_return)
            z_ann_vol = _zscore_series(ann_vol)
            z_mdd = _zscore_series(-asset_mdd)  # drawdown moins profond = meilleur score
            z_liquidity = _zscore_series(euro_volume)

            momentum_component = momentum_mult * (0.42 * z_m63 + 0.22 * z_m21 + 0.18 * z_m126 + 0.18 * z_ann_return)
            volatility_penalty_component = -vol_penalty * 0.90 * z_ann_vol
            drawdown_component = 0.25 * z_mdd
            liquidity_component = 0.12 * z_liquidity

            trend_raw = (
                0.33 * np.clip(ta_features["trend_distance"] / 0.06, -1.5, 1.5)
                + 0.27 * np.clip(ta_features["macd_hist"] / 0.02, -1.5, 1.5)
                + 0.20 * np.clip((ta_features["adx14"] - 22.0) / 18.0, -1.5, 1.5)
                + 0.20 * np.clip(ta_features["breakout20"] * 10.0, -1.5, 1.5)
                + 0.15 * ta_features["sma50_above_sma200"]
            )
            momentum_strategy_raw = (
                0.50 * np.clip(mom_63 * 4.0, -1.5, 1.5)
                + 0.30 * np.clip(mom_126 * 3.0, -1.5, 1.5)
                + 0.20 * np.clip(mom_21 * 6.0, -1.5, 1.5)
                + 0.10 * np.clip(ta_features["roc20"] * 8.0, -1.5, 1.5)
            )
            mean_reversion_raw = (
                0.40 * np.clip((50.0 - ta_features["rsi14"]) / 22.0, -1.5, 1.5)
                + 0.25 * np.clip((0.50 - ta_features["bb_pos"]) / 0.30, -1.5, 1.5)
                + 0.20 * np.clip((50.0 - ta_features["stoch_k"]) / 25.0, -1.5, 1.5)
                + 0.15 * np.clip(ta_features["pattern_signal"], -1.5, 1.5)
            )
            breakout_raw = (
                0.58 * np.clip(ta_features["breakout20"] * 12.0, -1.5, 1.5)
                + 0.24 * np.clip((ta_features["volume_ratio20"] - 1.0) / 0.8, -1.5, 1.5)
                + 0.18 * np.clip((ta_features["adx14"] - 25.0) / 15.0, -1.5, 1.5)
            )
            quality_risk_raw = (
                0.38 * _zscore_series(-ann_vol)
                + 0.27 * _zscore_series(-ta_features["atr_pct"])
                + 0.20 * _zscore_series(-asset_mdd)
                + 0.15 * _zscore_series(euro_volume)
            )

            trend_following_score = _zscore_series(pd.Series(trend_raw, index=close.columns))
            momentum_cross_sectional_score = _zscore_series(pd.Series(momentum_strategy_raw, index=close.columns))
            mean_reversion_score = _zscore_series(pd.Series(mean_reversion_raw, index=close.columns))
            breakout_score = _zscore_series(pd.Series(breakout_raw, index=close.columns))
            quality_risk_score = _zscore_series(pd.Series(quality_risk_raw, index=close.columns))
            legacy_composite = _zscore_series(
                momentum_component + volatility_penalty_component + drawdown_component + liquidity_component
            )

            technical_score = (
                strategy_weights["trend_following"] * trend_following_score
                + strategy_weights["momentum_cross_sectional"] * momentum_cross_sectional_score
                + strategy_weights["mean_reversion"] * mean_reversion_score
                + strategy_weights["breakout"] * breakout_score
                + strategy_weights["quality_risk_control"] * quality_risk_score
                + 0.18 * legacy_composite
            )

            logger.info(
                "[PEA][Scoring] Stratégies pondérées (%s): trend=%.2f momentum=%.2f mean_rev=%.2f breakout=%.2f quality=%.2f",
                risk_profile_key,
                strategy_weights["trend_following"],
                strategy_weights["momentum_cross_sectional"],
                strategy_weights["mean_reversion"],
                strategy_weights["breakout"],
                strategy_weights["quality_risk_control"],
            )
            logger.info(
                "[PEA][Scoring] Top trend_following: %s",
                [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(trend_following_score, top_n=6)],
            )
            logger.info(
                "[PEA][Scoring] Top momentum_cross_sectional: %s",
                [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(momentum_cross_sectional_score, top_n=6)],
            )
            logger.info(
                "[PEA][Scoring] Top breakout: %s",
                [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(breakout_score, top_n=6)],
            )
            logger.info(
                "[PEA][Scoring] Top scores techniques: %s",
                [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(technical_score, top_n=8)],
            )

            # Pré-sélection
            pool_size = min(len(technical_score), max(max_positions * 3, max_positions + 4))
            pool = list(technical_score.sort_values(ascending=False).head(pool_size).index)
            logger.info(
                "[PEA][Scoring] Pool présélectionné (%s): %s",
                len(pool),
                pool[:12],
            )

            # Score news
            news_signal = pd.Series(0.0, index=pool)
            news_headlines: Dict[str, List[str]] = {}
            use_news = _as_bool(use_yfinance_news)

            for ticker in pool:
                yf_signal = 0.0
                headlines: List[str] = []
                if use_news:
                    yf_signal, headlines = _yfinance_news_signal(ticker)
                ctx_signal = _context_signal_for_ticker(ticker, news_context)
                score = 0.70 * yf_signal + 0.30 * ctx_signal
                news_signal[ticker] = float(np.clip(score, -1.0, 1.0))
                if headlines:
                    news_headlines[ticker] = headlines

            if use_news:
                logger.info(
                    "[PEA][News] Top signaux news: %s",
                    [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(news_signal, top_n=8)],
                )
            else:
                logger.info("[PEA][News] News yfinance désactivées, score news basé sur news_context uniquement.")

            news_signal_z = _zscore_series(news_signal)
            tech_pool = technical_score[pool]
            tech_pool_z = _zscore_series(tech_pool)
            final_score = (1.0 - news_weight) * tech_pool_z + news_weight * news_signal_z
            logger.info(
                "[PEA][Scoring] Top score final (tech + news): %s",
                [f"{t}:{_fmt(s, 3)}" for t, s in _series_top(final_score, top_n=10)],
            )

            selected = list(final_score.sort_values(ascending=False).head(max_positions).index)
            if not selected:
                return json.dumps(
                    {"error": "Aucun ticker sélectionné après scoring."},
                    ensure_ascii=False,
                )
            logger.info("[PEA][Selection] Tickers retenus (%s): %s", len(selected), selected)
            for ticker in selected:
                logger.info(
                    "[PEA][Selection] %s | tech=%s | news=%s | final=%s | ann_return=%s | ann_vol=%s",
                    ticker,
                    _fmt(technical_score.get(ticker, 0.0), 4),
                    _fmt(news_signal.get(ticker, 0.0), 4),
                    _fmt(final_score.get(ticker, 0.0), 4),
                    _fmt(ann_return.get(ticker, 0.0), 4),
                    _fmt(ann_vol.get(ticker, 0.0), 4),
                )

            # Optimisation poids sur la sélection
            returns_sel = returns[selected]
            ann_return_sel = ann_return[selected]
            news_sel = news_signal[selected]
            trend_sel = trend_following_score[selected]
            momentum_sel = momentum_cross_sectional_score[selected]
            breakout_sel = breakout_score[selected]
            mean_rev_sel = mean_reversion_score[selected]

            # Boost de rendement attendu via news (borné)
            strategy_alpha = (
                0.012 * trend_sel
                + 0.015 * momentum_sel
                + 0.010 * breakout_sel
                + 0.006 * mean_rev_sel
            ).clip(-0.06, 0.10)
            expected_returns = (
                ann_return_sel
                + strategy_alpha
                + news_sel * (0.05 * news_weight)
            ).to_numpy(dtype=float)
            cov = (returns_sel.cov() * 252.0).to_numpy(dtype=float)

            max_weight = float(max_weight_pct / 100.0)
            if max_weight * len(selected) < 0.999:
                max_weight = min(1.0, 1.0 / len(selected) + 1e-6)
                warnings.append("Contrainte de poids max assouplie automatiquement pour conserver une solution faisable.")

            risk_aversion = RISK_PROFILES[risk_profile_key]
            weights, expected_ann_return, expected_ann_vol = _optimize_weights(
                expected_returns=expected_returns,
                covariance=cov,
                risk_aversion=risk_aversion,
                max_weight=max_weight,
            )
            logger.info(
                "[PEA][Optim] Poids optimisés: %s",
                [f"{ticker}:{_fmt(w * 100.0, 2)}%" for ticker, w in zip(selected, weights.tolist())],
            )
            logger.info(
                "[PEA][Optim] Metrics attendues (brut) | return=%s%% | vol=%s%% | risk_aversion=%s",
                _fmt(expected_ann_return * 100.0, 2),
                _fmt(expected_ann_vol * 100.0, 2),
                _fmt(risk_aversion, 3),
            )

            target_weights = {ticker: float(w) for ticker, w in zip(selected, weights.tolist())}

            # Construction des ordres (sells d'abord, puis buys)
            target_shares: Dict[str, int] = {}
            for ticker, weight in target_weights.items():
                target_value = portfolio_value_before * weight
                price = float(last_prices[ticker])
                qty = int(max(0.0, target_value) // max(price, 1e-9))
                target_shares[ticker] = qty

            simulated_positions: Dict[str, int] = {t: int(q) for t, q in current_positions.items() if int(q) > 0 and t in last_prices.index}
            for ticker in selected:
                simulated_positions.setdefault(ticker, 0)

            desired_positions = dict(target_shares)
            for ticker in list(simulated_positions.keys()):
                desired_positions.setdefault(ticker, 0)

            orders: List[Dict[str, Any]] = []
            total_costs = 0.0
            turnover = 0.0
            buy_count = 0
            sell_count = 0

            # Avertissement sur le profil de frais
            if (broker_fee_profile or "").strip().lower() == "credit_agricole_investore_integral":
                warnings.append(
                    "Frais Crédit Agricole modélisés de façon approximative (barème indicatif). Vérifier la tarification exacte de votre contrat."
                )

            # Sells
            sell_candidates = [t for t in desired_positions if desired_positions[t] < simulated_positions.get(t, 0)]
            for ticker in sell_candidates:
                current_qty = simulated_positions.get(ticker, 0)
                desired_qty = desired_positions.get(ticker, 0)
                qty = max(current_qty - desired_qty, 0)
                if qty <= 0:
                    continue

                price = float(last_prices[ticker])
                gross = qty * price
                cost = _calc_order_costs(
                    side="sell",
                    ticker=ticker,
                    gross_amount_eur=gross,
                    fee_profile=broker_fee_profile,
                    custom_fee_rate_pct=custom_fee_rate_pct,
                    custom_min_fee_eur=custom_min_fee_eur,
                    custom_fee_cap_pct=custom_fee_cap_pct,
                    slippage_pct=slippage_pct,
                    french_ftt_buy_pct=ftt_pct,
                )

                cash += cost["net_cash_impact_eur"]
                simulated_positions[ticker] = current_qty - qty
                if simulated_positions[ticker] <= 0:
                    simulated_positions.pop(ticker, None)

                order = {
                    "side": "SELL",
                    "ticker": ticker,
                    "quantity": int(qty),
                    "estimated_price_eur": round(price, 4),
                    "reason": "Réduction/rotation vers allocation cible optimisée",
                }
                order.update({k: round(v, 4) for k, v in cost.items()})
                orders.append(order)
                logger.info(
                    "[PEA][Order] SELL %s x%s @ %s | gross=%s | fee=%s | slippage=%s | ftt=%s | cash_impact=%s",
                    ticker,
                    qty,
                    _fmt(price, 4),
                    _fmt(cost["gross_amount_eur"], 2),
                    _fmt(cost["broker_fee_eur"], 2),
                    _fmt(cost["slippage_eur"], 2),
                    _fmt(cost["ftt_eur"], 2),
                    _fmt(cost["net_cash_impact_eur"], 2),
                )

                total_costs += cost["broker_fee_eur"] + cost["slippage_eur"] + cost["ftt_eur"]
                turnover += gross
                sell_count += 1

            # Buys (priorisés par score final)
            buy_candidates = [t for t in selected if desired_positions.get(t, 0) > simulated_positions.get(t, 0)]
            buy_candidates.sort(key=lambda t: float(final_score.get(t, 0.0)), reverse=True)

            for ticker in buy_candidates:
                desired_qty = desired_positions.get(ticker, 0)
                current_qty = simulated_positions.get(ticker, 0)
                qty_needed = max(desired_qty - current_qty, 0)
                if qty_needed <= 0:
                    continue

                price = float(last_prices[ticker])
                qty = qty_needed
                affordable_qty = 0

                while qty > 0:
                    gross = qty * price
                    cost = _calc_order_costs(
                        side="buy",
                        ticker=ticker,
                        gross_amount_eur=gross,
                        fee_profile=broker_fee_profile,
                        custom_fee_rate_pct=custom_fee_rate_pct,
                        custom_min_fee_eur=custom_min_fee_eur,
                        custom_fee_cap_pct=custom_fee_cap_pct,
                        slippage_pct=slippage_pct,
                        french_ftt_buy_pct=ftt_pct,
                    )
                    needed_cash = -cost["net_cash_impact_eur"]
                    if cash + 1e-9 >= needed_cash:
                        affordable_qty = qty
                        break
                    qty -= 1

                if affordable_qty <= 0:
                    warnings.append(
                        f"Cash insuffisant pour acheter {ticker} à la taille cible (coûts inclus)."
                    )
                    continue

                gross = affordable_qty * price
                cost = _calc_order_costs(
                    side="buy",
                    ticker=ticker,
                    gross_amount_eur=gross,
                    fee_profile=broker_fee_profile,
                    custom_fee_rate_pct=custom_fee_rate_pct,
                    custom_min_fee_eur=custom_min_fee_eur,
                    custom_fee_cap_pct=custom_fee_cap_pct,
                    slippage_pct=slippage_pct,
                    french_ftt_buy_pct=ftt_pct,
                )

                cash += cost["net_cash_impact_eur"]
                simulated_positions[ticker] = simulated_positions.get(ticker, 0) + affordable_qty

                order = {
                    "side": "BUY",
                    "ticker": ticker,
                    "quantity": int(affordable_qty),
                    "estimated_price_eur": round(price, 4),
                    "reason": "Construction/renforcement vers allocation cible optimisée",
                }
                order.update({k: round(v, 4) for k, v in cost.items()})
                orders.append(order)
                logger.info(
                    "[PEA][Order] BUY %s x%s @ %s | gross=%s | fee=%s | slippage=%s | ftt=%s | cash_impact=%s",
                    ticker,
                    affordable_qty,
                    _fmt(price, 4),
                    _fmt(cost["gross_amount_eur"], 2),
                    _fmt(cost["broker_fee_eur"], 2),
                    _fmt(cost["slippage_eur"], 2),
                    _fmt(cost["ftt_eur"], 2),
                    _fmt(cost["net_cash_impact_eur"], 2),
                )

                total_costs += cost["broker_fee_eur"] + cost["slippage_eur"] + cost["ftt_eur"]
                turnover += gross
                buy_count += 1

            # Valorisation après exécution simulée
            final_positions_value = 0.0
            realized_alloc: List[Dict[str, Any]] = []
            for ticker, shares in sorted(simulated_positions.items()):
                if ticker not in last_prices.index or shares <= 0:
                    continue
                price = float(last_prices[ticker])
                value = float(shares) * price
                final_positions_value += value
                realized_alloc.append(
                    {
                        "ticker": ticker,
                        "shares": int(shares),
                        "latest_price_eur": round(price, 4),
                        "market_value_eur": round(value, 2),
                    }
                )

            portfolio_value_after = float(cash + final_positions_value)
            realized_weights: Dict[str, float] = {}
            if portfolio_value_after > 0:
                for item in realized_alloc:
                    realized_weights[item["ticker"]] = item["market_value_eur"] / portfolio_value_after

            for item in realized_alloc:
                w = realized_weights.get(item["ticker"], 0.0)
                item["weight_pct"] = round(w * 100.0, 2)

            # Allocation cible théorique
            target_allocation: List[Dict[str, Any]] = []
            for ticker in sorted(selected, key=lambda t: target_weights[t], reverse=True):
                price = float(last_prices[ticker])
                weight = float(target_weights[ticker])
                target_value = portfolio_value_before * weight
                target_allocation.append(
                    {
                        "ticker": ticker,
                        "target_weight_pct": round(weight * 100.0, 2),
                        "target_value_eur": round(target_value, 2),
                        "target_shares": int(target_shares.get(ticker, 0)),
                        "latest_price_eur": round(price, 4),
                        "technical_score": round(float(technical_score.get(ticker, 0.0)), 4),
                        "news_score": round(float(news_signal.get(ticker, 0.0)), 4),
                        "final_score": round(float(final_score.get(ticker, 0.0)), 4),
                    }
                )

            def _pattern_label(score: float) -> str:
                if score >= 0.8:
                    return "bullish_engulfing_or_hammer"
                if score <= -0.8:
                    return "bearish_engulfing_or_shooting_star"
                return "neutral_or_doji"

            def _build_indicator_row(ticker: str) -> Dict[str, Any]:
                pattern_val = float(ta_features["pattern_signal"].get(ticker, 0.0))
                return {
                    "ticker": ticker,
                    "momentum_1m_pct": round(float(mom_21.get(ticker, 0.0)) * 100.0, 2),
                    "momentum_3m_pct": round(float(mom_63.get(ticker, 0.0)) * 100.0, 2),
                    "momentum_6m_pct": round(float(mom_126.get(ticker, 0.0)) * 100.0, 2),
                    "annualized_return_pct": round(float(ann_return.get(ticker, 0.0)) * 100.0, 2),
                    "annualized_volatility_pct": round(float(ann_vol.get(ticker, 0.0)) * 100.0, 2),
                    "max_drawdown_pct": round(float(asset_mdd.get(ticker, 0.0)) * 100.0, 2),
                    "liquidity_eur_avg_60d": round(float(euro_volume.get(ticker, 0.0)), 2),
                    "rsi_14": round(float(ta_features["rsi14"].get(ticker, 50.0)), 2),
                    "macd_line": round(float(ta_features["macd_line"].get(ticker, 0.0)), 4),
                    "macd_signal": round(float(ta_features["macd_signal"].get(ticker, 0.0)), 4),
                    "macd_hist": round(float(ta_features["macd_hist"].get(ticker, 0.0)), 4),
                    "atr_pct": round(float(ta_features["atr_pct"].get(ticker, 0.0)) * 100.0, 2),
                    "adx_14": round(float(ta_features["adx14"].get(ticker, 20.0)), 2),
                    "bollinger_position": round(float(ta_features["bb_pos"].get(ticker, 0.5)), 3),
                    "bollinger_width_pct": round(float(ta_features["bb_width"].get(ticker, 0.0)) * 100.0, 2),
                    "stochastic_k": round(float(ta_features["stoch_k"].get(ticker, 50.0)), 2),
                    "stochastic_d": round(float(ta_features["stoch_d"].get(ticker, 50.0)), 2),
                    "breakout_20d_pct": round(float(ta_features["breakout20"].get(ticker, 0.0)) * 100.0, 2),
                    "volume_ratio_20d": round(float(ta_features["volume_ratio20"].get(ticker, 1.0)), 2),
                    "roc_20d_pct": round(float(ta_features["roc20"].get(ticker, 0.0)) * 100.0, 2),
                    "candlestick_pattern_signal": round(pattern_val, 2),
                    "candlestick_pattern_label": _pattern_label(pattern_val),
                    "score_components": {
                        "momentum_component": round(float(momentum_component.get(ticker, 0.0)), 4),
                        "volatility_penalty_component": round(float(volatility_penalty_component.get(ticker, 0.0)), 4),
                        "drawdown_component": round(float(drawdown_component.get(ticker, 0.0)), 4),
                        "liquidity_component": round(float(liquidity_component.get(ticker, 0.0)), 4),
                        "trend_following_score": round(float(trend_following_score.get(ticker, 0.0)), 4),
                        "momentum_cross_sectional_score": round(float(momentum_cross_sectional_score.get(ticker, 0.0)), 4),
                        "mean_reversion_score": round(float(mean_reversion_score.get(ticker, 0.0)), 4),
                        "breakout_score": round(float(breakout_score.get(ticker, 0.0)), 4),
                        "quality_risk_score": round(float(quality_risk_score.get(ticker, 0.0)), 4),
                    },
                    "signal_bias": (
                        "strong_buy"
                        if float(technical_score.get(ticker, 0.0)) >= 1.0
                        else "buy"
                        if float(technical_score.get(ticker, 0.0)) >= 0.25
                        else "neutral"
                        if float(technical_score.get(ticker, 0.0)) > -0.25
                        else "reduce"
                    ),
                    "technical_score": round(float(technical_score.get(ticker, 0.0)), 4),
                    "news_score": round(float(news_signal.get(ticker, 0.0)), 4),
                    "final_score": round(float(final_score.get(ticker, 0.0)), 4),
                }

            selected_sorted = list(final_score[selected].sort_values(ascending=False).index)
            alternatives = [t for t in final_score.sort_values(ascending=False).index if t not in selected]
            alternatives = alternatives[: max(3, min(max_positions, 8))]

            technical_analysis = {
                "methodology": {
                    "description": (
                        "Ensemble multi-stratégies inspiré des pratiques de desks actions institutionnels: "
                        "trend-following, momentum cross-sectionnel, mean-reversion, breakout, quality/risk control. "
                        "Le score final combine signal technique et signal actualité."
                    ),
                    "risk_profile": risk_profile_key,
                    "momentum_multiplier": round(momentum_mult, 3),
                    "volatility_penalty": round(vol_penalty, 3),
                    "strategy_weights": {
                        k: round(float(v), 3) for k, v in strategy_weights.items()
                    },
                    "news_weight_pct": round(news_weight_pct, 2),
                },
                "selected_tickers_indicators": [_build_indicator_row(t) for t in selected_sorted],
                "top_alternatives_not_selected": [_build_indicator_row(t) for t in alternatives],
            }

            # Métriques attendues
            portfolio_returns = (returns_sel * weights).sum(axis=1)
            hist_annual_return = float((1.0 + portfolio_returns.mean()) ** 252 - 1.0)
            hist_annual_vol = float(portfolio_returns.std() * np.sqrt(252.0))
            sharpe = hist_annual_return / hist_annual_vol if hist_annual_vol > 1e-12 else None
            mdd = _max_drawdown(portfolio_returns)

            cost_ratio = total_costs / max(portfolio_value_before, 1e-9)
            expected_net_return = expected_ann_return - cost_ratio
            logger.info(
                "[PEA][Synthèse] Ordres: BUY=%s SELL=%s | turnover=%s | coûts=%s (%s%%)",
                buy_count,
                sell_count,
                _fmt(turnover, 2),
                _fmt(total_costs, 2),
                _fmt(cost_ratio * 100.0, 2),
            )
            logger.info(
                "[PEA][Synthèse] Perf attendue | brut=%s%% | net 1er rebalance=%s%%",
                _fmt(expected_ann_return * 100.0, 2),
                _fmt(expected_net_return * 100.0, 2),
            )
            logger.info(
                "[PEA][Synthèse] Capital après ordres | cash=%s | positions=%s | total=%s",
                _fmt(cash, 2),
                _fmt(final_positions_value, 2),
                _fmt(portfolio_value_after, 2),
            )

            # Snapshot actualité retenue pour auditabilité
            news_snapshot = []
            for ticker in selected:
                if ticker in news_headlines and news_headlines[ticker]:
                    news_snapshot.append(
                        {
                            "ticker": ticker,
                            "headlines": news_headlines[ticker][:3],
                            "news_score": round(float(news_signal.get(ticker, 0.0)), 4),
                        }
                    )

            response = {
                "as_of": str(close.index[-1].date()),
                "risk_profile": risk_profile_key,
                "broker_fee_profile": broker_fee_profile,
                "capital": {
                    "cash_avant_eur": round(float(cash_before_rebalance), 2),
                    "positions_value_avant_eur": round(positions_value_before, 2),
                    "valeur_portefeuille_avant_eur": round(portfolio_value_before, 2),
                    "cash_apres_ordres_eur": round(float(cash), 2),
                    "positions_value_apres_eur": round(final_positions_value, 2),
                    "valeur_portefeuille_apres_eur": round(portfolio_value_after, 2),
                },
                "selection": {
                    "universe_requested": requested_tickers,
                    "universe_used": tradable_tickers,
                    "tickers_rejected": rejected_tickers,
                    "tickers_selectionnes": selected,
                },
                "target_allocation": target_allocation,
                "realized_allocation": realized_alloc,
                "technical_analysis": technical_analysis,
                "orders": orders,
                "orders_summary": {
                    "buy_orders": buy_count,
                    "sell_orders": sell_count,
                    "turnover_eur": round(turnover, 2),
                    "estimated_transaction_costs_eur": round(total_costs, 2),
                    "estimated_cost_ratio_pct": round(cost_ratio * 100.0, 2),
                },
                "expected_metrics": {
                    "expected_annual_return_gross_pct": round(expected_ann_return * 100.0, 2),
                    "expected_annual_return_net_first_rebalance_pct": round(expected_net_return * 100.0, 2),
                    "expected_annual_volatility_pct": round(expected_ann_vol * 100.0, 2),
                    "historical_annual_return_pct": round(hist_annual_return * 100.0, 2),
                    "historical_annual_volatility_pct": round(hist_annual_vol * 100.0, 2),
                    "historical_sharpe_ratio": round(float(sharpe), 3) if sharpe is not None else None,
                    "historical_max_drawdown_pct": round(mdd * 100.0, 2),
                },
                "news_snapshot": news_snapshot,
                "portfolio_tracking": {
                    "portfolio_id": portfolio_id_safe,
                    "persistence_enabled": bool(persistence_enabled),
                    "state_file": str(state_path),
                    "loaded_existing_state": bool(loaded_state_used),
                },
                "disclaimer": (
                    "Simulation éducative: pas un conseil financier personnalisé. "
                    "Les coûts/frais sont estimés (dont barème Crédit Agricole approximatif), "
                    "sans garantie d'éligibilité PEA réelle, de liquidité, ni d'exécution au prix théorique."
                ),
            }

            if persistence_enabled:
                now_utc = datetime.now(timezone.utc).isoformat()
                prior_runs: List[Dict[str, Any]] = []
                if loaded_state_payload and isinstance(loaded_state_payload, dict):
                    candidate_runs = loaded_state_payload.get("runs")
                    if isinstance(candidate_runs, list):
                        prior_runs = [r for r in candidate_runs if isinstance(r, dict)]

                run_record = {
                    "generated_at_utc": now_utc,
                    "as_of": str(close.index[-1].date()),
                    "inputs": {
                        "risk_profile": risk_profile_key,
                        "lookback_years": lookback_years,
                        "max_positions": max_positions,
                        "max_weight_pct": max_weight_pct,
                        "news_weight_pct": news_weight_pct,
                        "broker_fee_profile": broker_fee_profile,
                        "slippage_pct": slippage_pct,
                        "french_ftt_buy_pct": ftt_pct,
                        "state_loaded": bool(loaded_state_used),
                    },
                    "selection": response["selection"],
                    "orders": orders,
                    "orders_summary": response["orders_summary"],
                    "capital": response["capital"],
                    "expected_metrics": response["expected_metrics"],
                    "technical_analysis": technical_analysis,
                    "warnings": list(warnings),
                }
                all_runs = prior_runs + [run_record]
                if len(all_runs) > max_saved_runs:
                    all_runs = all_runs[-max_saved_runs:]

                state_payload = {
                    "portfolio_id": portfolio_id_safe,
                    "created_at": (
                        loaded_state_payload.get("created_at")
                        if isinstance(loaded_state_payload, dict) and loaded_state_payload.get("created_at")
                        else now_utc
                    ),
                    "last_updated_at": now_utc,
                    "state": {
                        "cash_eur": round(float(cash), 2),
                        "positions": {str(t): int(q) for t, q in simulated_positions.items() if int(q) > 0},
                        "portfolio_value_eur": round(float(portfolio_value_after), 2),
                        "as_of": str(close.index[-1].date()),
                    },
                    "runs": all_runs,
                }
                save_err = _save_portfolio_state(state_path, state_payload)
                if save_err:
                    warnings.append(save_err)
                    response["portfolio_tracking"]["state_saved"] = False
                    response["portfolio_tracking"]["save_error"] = save_err
                else:
                    performance_since_first = None
                    if all_runs:
                        first_capital = all_runs[0].get("capital", {}) if isinstance(all_runs[0], dict) else {}
                        try:
                            base_value = float(
                                first_capital.get("valeur_portefeuille_apres_eur")
                                or first_capital.get("valeur_portefeuille_avant_eur")
                                or 0.0
                            )
                            if base_value > 0:
                                performance_since_first = (portfolio_value_after / base_value - 1.0) * 100.0
                        except Exception:
                            performance_since_first = None

                    response["portfolio_tracking"]["state_saved"] = True
                    response["portfolio_tracking"]["runs_count"] = len(all_runs)
                    response["portfolio_tracking"]["last_run_utc"] = now_utc
                    if performance_since_first is not None:
                        response["portfolio_tracking"]["performance_since_first_run_pct"] = round(
                            float(performance_since_first), 2
                        )
                    logger.info(
                        "[PEA][Tracking] État sauvegardé | file=%s | runs=%s",
                        str(state_path),
                        len(all_runs),
                    )

            response["warnings"] = warnings
            logger.info("[PEA][Plan] Fin génération | warnings=%s", len(warnings))
            if warnings:
                logger.info("[PEA][Plan] Warnings (extrait): %s", warnings[:8])
            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("[PEAPortfolioTools] Erreur durant la génération du plan de trading: %s", e)
            return json.dumps(
                {"error": f"Erreur pendant la génération du plan de trading PEA: {str(e)}"},
                ensure_ascii=False,
            )

    @tool(
        description=(
            "Compatibilité historique: optimise une allocation initiale PEA simulée à partir d'un capital "
            "et d'une liste de tickers."
        )
    )
    def optimize_pea_portfolio(
        self,
        initial_capital_eur: float,
        tickers: str,
        risk_profile: str = "equilibre",
        lookback_years: int = 3,
        max_weight_pct: float = 35.0,
        max_assets: int = 8,
    ) -> str:
        """
        Wrapper de compatibilité: construit un plan initial sans positions existantes.
        """
        try:
            raw = self.generate_pea_trading_plan(
                available_cash_eur=initial_capital_eur,
                current_positions_json="[]",
                candidate_tickers=tickers,
                risk_profile=risk_profile,
                lookback_years=lookback_years,
                max_positions=max_assets,
                max_weight_pct=max_weight_pct,
                news_weight_pct=0.0,
                news_context="",
                use_yfinance_news=False,
                broker_fee_profile="credit_agricole_investore_integral",
                estimated_slippage_pct=0.0,
            )
            plan = json.loads(raw)
            if "error" in plan:
                if "rejected_tickers" in plan and "tickers_rejetes" not in plan:
                    plan["tickers_rejetes"] = plan.get("rejected_tickers", [])
                return json.dumps(plan, ensure_ascii=False, indent=2)

            alloc = []
            invested_total = 0.0
            for item in plan.get("realized_allocation", []):
                invested = float(item.get("market_value_eur", 0.0))
                invested_total += invested
                alloc.append(
                    {
                        "ticker": item.get("ticker"),
                        "weight_pct": item.get("weight_pct"),
                        "latest_price": item.get("latest_price_eur"),
                        "target_amount_eur": item.get("market_value_eur"),
                        "shares": item.get("shares"),
                        "invested_amount_eur": item.get("market_value_eur"),
                    }
                )

            metrics = plan.get("expected_metrics", {})
            response = {
                "capital_initial_eur": round(float(initial_capital_eur), 2),
                "capital_investi_eur": round(invested_total, 2),
                "cash_restant_eur": round(float(plan.get("capital", {}).get("cash_apres_ordres_eur", 0.0)), 2),
                "risk_profile": risk_profile,
                "lookback_years": int(lookback_years),
                "max_weight_pct": float(max_weight_pct),
                "tickers_retenus": [x.get("ticker") for x in alloc if x.get("ticker")],
                "tickers_rejetes": plan.get("selection", {}).get("tickers_rejected", []),
                "allocation": alloc,
                "metrics": {
                    "expected_annual_return_pct": metrics.get("expected_annual_return_gross_pct"),
                    "expected_annual_volatility_pct": metrics.get("expected_annual_volatility_pct"),
                    "historical_annual_return_pct": metrics.get("historical_annual_return_pct"),
                    "historical_annual_volatility_pct": metrics.get("historical_annual_volatility_pct"),
                    "historical_sharpe_ratio": metrics.get("historical_sharpe_ratio"),
                    "historical_max_drawdown_pct": metrics.get("historical_max_drawdown_pct"),
                },
                "method": {
                    "type": "score momentum/volatilite + optimisation long-only",
                    "objective": "maximiser rendement espere ajuste du risque",
                    "risk_aversion": RISK_PROFILES.get(str(risk_profile).lower(), RISK_PROFILES["equilibre"]),
                    "trading_style": "long_only",
                    "rebalancing": "allocation initiale",
                },
                "as_of": plan.get("as_of"),
                "warnings": plan.get("warnings", []),
                "disclaimer": plan.get("disclaimer"),
            }
            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("[PEAPortfolioTools] Erreur durant l'optimisation legacy: %s", e)
            return json.dumps(
                {"error": f"Erreur pendant l'optimisation PEA simulée: {str(e)}"},
                ensure_ascii=False,
            )
