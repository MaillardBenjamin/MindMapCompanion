import json
from typing import List

import numpy as np
import pandas as pd

from app.tools.pea_portfolio_tools import PEAPortfolioTools


def _parse_tickers_arg(tickers) -> List[str]:
    if isinstance(tickers, str):
        return [x.strip().upper() for x in tickers.split(",") if x.strip()]
    if isinstance(tickers, (list, tuple)):
        return [str(x).strip().upper() for x in tickers if str(x).strip()]
    return []


def _mock_market_data(tickers: List[str]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", periods=280)
    t = np.arange(len(dates), dtype=float)

    # ORA.PA est volontairement en tendance négative pour forcer des arbitrages SELL dans un test.
    growth_map = {
        "MC.PA": 0.00095,
        "AIR.PA": 0.00070,
        "SAN.PA": 0.00045,
        "ORA.PA": -0.00030,
        "ASML.AS": 0.00090,
        "SAP.DE": 0.00065,
    }

    data = {}
    for idx, ticker in enumerate(tickers):
        growth = growth_map.get(ticker, 0.00035)
        base = 80.0 + 5.0 * idx
        close = base * ((1.0 + growth) ** t)
        open_ = close * (1.0 + 0.0007 * np.sin(t / 6.0 + idx))
        high = np.maximum(open_, close) * (1.0 + 0.0045)
        low = np.minimum(open_, close) * (1.0 - 0.0045)
        volume = np.full(len(dates), 450_000 + idx * 25_000, dtype=float)

        data[("Open", ticker)] = open_
        data[("High", ticker)] = high
        data[("Low", ticker)] = low
        data[("Close", ticker)] = close
        data[("Volume", ticker)] = volume

    frame = pd.DataFrame(data, index=dates)
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame


class _FakeTicker:
    def __init__(self, ticker: str):
        self.ticker = ticker

    @property
    def news(self):
        positive = [{"title": "Croissance solide", "summary": "hausse des perspectives"}]
        negative = [{"title": "Warning sur marges", "summary": "pression et ralentissement"}]

        if self.ticker in {"MC.PA", "ASML.AS"}:
            return positive
        if self.ticker in {"ORA.PA"}:
            return negative
        return []


def test_generate_pea_trading_plan_auto_selection_and_buy_orders(monkeypatch):
    def fake_download(*args, **kwargs):
        tickers = _parse_tickers_arg(kwargs.get("tickers") or (args[0] if args else ""))
        return _mock_market_data(tickers)

    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.download", fake_download)
    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.Ticker", _FakeTicker)

    toolkit = PEAPortfolioTools()
    raw = toolkit.generate_pea_trading_plan(
        available_cash_eur=15000,
        current_positions_json="[]",
        candidate_tickers="MC.PA, AIR.PA, SAN.PA, ORA.PA",
        risk_profile="dynamique",
        lookback_years=3,
        max_positions=3,
        max_weight_pct=45.0,
        news_weight_pct=20.0,
        news_context="MC.PA et AIR.PA sur une dynamique de croissance, ORA.PA en baisse",
        use_yfinance_news=True,
        broker_fee_profile="credit_agricole_investore_integral",
    )
    result = json.loads(raw)

    assert "error" not in result
    assert result["selection"]["tickers_selectionnes"]
    assert len(result["selection"]["tickers_selectionnes"]) <= 3
    assert any(order["side"] == "BUY" for order in result["orders"])
    assert result["orders_summary"]["estimated_transaction_costs_eur"] >= 0
    assert "technical_analysis" in result
    assert result["technical_analysis"]["selected_tickers_indicators"]


def test_generate_pea_trading_plan_creates_sell_order_when_rotation_needed(monkeypatch):
    def fake_download(*args, **kwargs):
        tickers = _parse_tickers_arg(kwargs.get("tickers") or (args[0] if args else ""))
        return _mock_market_data(tickers)

    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.download", fake_download)
    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.Ticker", _FakeTicker)

    toolkit = PEAPortfolioTools()
    raw = toolkit.generate_pea_trading_plan(
        available_cash_eur=1000,
        current_positions_json='[{"ticker":"ORA.PA","shares":40}]',
        candidate_tickers="MC.PA, AIR.PA, SAN.PA, ORA.PA",
        risk_profile="equilibre",
        lookback_years=3,
        max_positions=2,
        max_weight_pct=60.0,
        news_weight_pct=30.0,
        news_context="ORA.PA sous pression, MC.PA en surperformance",
        use_yfinance_news=True,
    )
    result = json.loads(raw)

    assert "error" not in result
    assert any(order["side"] == "SELL" and order["ticker"] == "ORA.PA" for order in result["orders"])


def test_generate_pea_trading_plan_accepts_alias_arguments(monkeypatch):
    def fake_download(*args, **kwargs):
        tickers = _parse_tickers_arg(kwargs.get("tickers") or (args[0] if args else ""))
        return _mock_market_data(tickers)

    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.download", fake_download)
    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.Ticker", _FakeTicker)

    toolkit = PEAPortfolioTools()
    raw = toolkit.generate_pea_trading_plan(
        available_cash=5000,
        current_positions='[{"ticker":"ORA.PA","shares":5}]',
        candidate_tickers="MC.PA, AIR.PA, SAN.PA, ORA.PA",
        risk_profile="dynamic",
        lookback_period=3,
        max_positions=3,
        max_weight_pct=40.0,
        news_weight_pct=15.0,
    )
    result = json.loads(raw)

    assert "error" not in result
    assert result["selection"]["tickers_selectionnes"]


def test_generate_pea_trading_plan_persistent_state_roundtrip(monkeypatch, tmp_path):
    def fake_download(*args, **kwargs):
        tickers = _parse_tickers_arg(kwargs.get("tickers") or (args[0] if args else ""))
        return _mock_market_data(tickers)

    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.download", fake_download)
    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.Ticker", _FakeTicker)

    toolkit = PEAPortfolioTools()
    state_file = tmp_path / "pea_state.json"

    raw_1 = toolkit.generate_pea_trading_plan(
        available_cash_eur=5000,
        current_positions_json="[]",
        candidate_tickers="MC.PA, AIR.PA, SAN.PA, ORA.PA",
        risk_profile="equilibre",
        lookback_years=3,
        max_positions=3,
        max_weight_pct=40.0,
        news_weight_pct=20.0,
        use_yfinance_news=True,
        portfolio_id="test_portfolio",
        persist_portfolio_state=True,
        portfolio_state_file=str(state_file),
    )
    result_1 = json.loads(raw_1)
    assert "error" not in result_1
    assert result_1["portfolio_tracking"]["state_saved"] is True
    assert state_file.exists()

    raw_2 = toolkit.generate_pea_trading_plan(
        available_cash_eur=999999,  # doit être ignoré si l'état persistant est chargé
        current_positions_json="[]",
        candidate_tickers="MC.PA, AIR.PA, SAN.PA, ORA.PA",
        risk_profile="equilibre",
        lookback_years=3,
        max_positions=3,
        max_weight_pct=40.0,
        news_weight_pct=20.0,
        use_yfinance_news=True,
        portfolio_id="test_portfolio",
        persist_portfolio_state=True,
        portfolio_state_file=str(state_file),
    )
    result_2 = json.loads(raw_2)
    assert "error" not in result_2
    assert result_2["portfolio_tracking"]["loaded_existing_state"] is True
    assert result_2["portfolio_tracking"]["state_saved"] is True
    assert result_2["portfolio_tracking"]["runs_count"] == 2


def test_optimize_pea_portfolio_returns_allocation(monkeypatch):
    def fake_download(*args, **kwargs):
        tickers = _parse_tickers_arg(kwargs.get("tickers") or (args[0] if args else ""))
        return _mock_market_data(tickers)

    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.download", fake_download)
    monkeypatch.setattr("app.tools.pea_portfolio_tools.yf.Ticker", _FakeTicker)

    toolkit = PEAPortfolioTools()
    raw = toolkit.optimize_pea_portfolio(
        initial_capital_eur=10000,
        tickers="MC.PA, AIR.PA, SAN.PA",
        risk_profile="dynamique",
        lookback_years=3,
        max_weight_pct=60.0,
        max_assets=3,
    )
    result = json.loads(raw)

    assert "error" not in result
    assert result["allocation"]
    assert result["capital_initial_eur"] == 10000
    assert result["capital_investi_eur"] <= result["capital_initial_eur"]


def test_optimize_pea_portfolio_rejects_non_eu_suffixes():
    toolkit = PEAPortfolioTools()
    raw = toolkit.optimize_pea_portfolio(
        initial_capital_eur=10000,
        tickers="AAPL, MSFT",
        risk_profile="equilibre",
        lookback_years=3,
        max_weight_pct=35.0,
        max_assets=8,
    )
    result = json.loads(raw)

    assert "error" in result
    assert result.get("tickers_rejetes") == ["AAPL", "MSFT"]
