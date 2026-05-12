"""
Financial data tools wrapping akshare for A-share market data.

Tools are organized into three categories:
- COMPANY_TOOLS: Individual stock data (registered in investment-company toolset)
- MARKET_TOOLS: Market/index/macro data (registered in investment-market toolset)
- SHARED_TOOLS: Cross-cutting quant data (registered in both toolsets)
"""

import json
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECONDS = 0.3


def _rate_limit():
    time.sleep(_RATE_LIMIT_SECONDS)


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _error_response(error: str, hint: str = "") -> str:
    resp = {"status": "error", "error": error}
    if hint:
        resp["hint"] = hint
    return _safe_json(resp)


def _ok_response(data: Any) -> str:
    return _safe_json({"status": "ok", "data": data})


# =============================================================================
# COMPANY-LEVEL TOOLS (investment-company toolset)
# =============================================================================


def fetch_stock_financials_handler(stock_code: str, data_type: str = "metrics", **kwargs) -> str:
    """Fetch financial data for an A-share stock."""
    import akshare as ak
    _rate_limit()
    try:
        if data_type == "metrics":
            df = ak.stock_financial_abstract_ths(symbol=stock_code)
        elif data_type == "income":
            df = ak.stock_profit_sheet_by_report_em(symbol=stock_code)
        elif data_type == "balance":
            df = ak.stock_balance_sheet_by_report_em(symbol=stock_code)
        elif data_type == "cashflow":
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=stock_code)
        else:
            return _error_response(f"Unknown data_type: {data_type}", "Use: metrics, income, balance, cashflow")

        if df is None or df.empty:
            return _error_response(f"No data returned for {stock_code}")

        # Data sorted old→new; return most recent 20 periods
        records = df.tail(20).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Check stock code (6 digits, e.g. 002415) or try again later")


def fetch_stock_price_handler(stock_code: str, period: str = "daily", days: int = 120, **kwargs) -> str:
    """Fetch historical price data for an A-share stock."""
    import akshare as ak
    _rate_limit()
    try:
        # Determine market prefix: 6xxxxx = Shanghai (sh), others = Shenzhen (sz)
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df is None or df.empty:
            return _error_response(f"No price data for {stock_code}")

        records = df.tail(days).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Check stock code format (6 digits) or try again")


def fetch_stock_info_handler(stock_code: str, **kwargs) -> str:
    """Fetch basic information for an A-share stock using financial abstract and price data."""
    import akshare as ak
    _rate_limit()
    try:
        info = {"stock_code": stock_code}

        # Get latest price data
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df_price = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df_price is not None and not df_price.empty:
            latest = df_price.iloc[-1]
            info["latest_price"] = float(latest["close"])
            info["latest_date"] = str(latest["date"])
            info["volume"] = int(latest["volume"])

        _rate_limit()
        # Get financial metrics (data sorted old→new, latest is last row)
        df_fin = ak.stock_financial_abstract_ths(symbol=stock_code)
        if df_fin is not None and not df_fin.empty:
            latest_fin = df_fin.iloc[-1]
            info["report_period"] = str(latest_fin.get("报告期", ""))
            info["eps"] = str(latest_fin.get("基本每股收益", ""))
            info["nav_per_share"] = str(latest_fin.get("每股净资产", ""))
            info["revenue"] = str(latest_fin.get("营业总收入", ""))
            info["net_profit"] = str(latest_fin.get("净利润", ""))
            info["revenue_growth"] = str(latest_fin.get("营业总收入同比增长率", ""))
            info["profit_growth"] = str(latest_fin.get("净利润同比增长率", ""))

        return _ok_response(info)
    except Exception as e:
        return _error_response(str(e))


def fetch_industry_constituents_handler(industry: str, **kwargs) -> str:
    """Fetch list of stocks in a given industry sector."""
    import akshare as ak
    _rate_limit()
    try:
        # Try eastmoney backend first (most comprehensive)
        try:
            df = ak.stock_board_industry_cons_em(symbol=industry)
            if df is not None and not df.empty:
                cols = ["代码", "名称", "最新价", "涨跌幅", "总市值"]
                available_cols = [c for c in cols if c in df.columns]
                records = df[available_cols].head(50).to_dict(orient="records")
                return _ok_response(records)
        except Exception:
            pass

        # Fallback: return industry summary from ths
        _rate_limit()
        try:
            df_summary = ak.stock_board_industry_summary_ths()
            if df_summary is not None and not df_summary.empty:
                match = df_summary[df_summary["板块"].str.contains(industry, na=False)]
                if not match.empty:
                    records = match.head(5).to_dict(orient="records")
                    return _ok_response({"note": "Detailed constituents unavailable (network), showing industry summary", "data": records})
        except Exception:
            pass

        return _error_response(
            f"Cannot fetch constituents for '{industry}' (network restriction on data source)",
            "Use Chinese industry name (e.g. '半导体'). Try searching individual stocks with fetch_stock_info instead."
        )
    except Exception as e:
        return _error_response(str(e), "Use Chinese industry name, e.g. '半导体', '白酒', '光伏设备'")


# =============================================================================
# MARKET-LEVEL TOOLS (investment-market toolset)
# =============================================================================


def fetch_market_index_handler(index_code: str = "000300", days: int = 60, **kwargs) -> str:
    """Fetch index data (price + valuation). Common indices: 000300 (CSI300), 000001 (SSE Composite), 399006 (ChiNext)."""
    import akshare as ak
    _rate_limit()
    try:
        df = ak.stock_zh_index_daily(symbol=f"sh{index_code}" if index_code.startswith("0") else f"sz{index_code}")
        if df is None or df.empty:
            return _error_response(f"No data for index {index_code}")

        records = df.tail(days).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Common indices: 000300 (CSI300), 000001 (SSE), 399006 (ChiNext), 000905 (CSI500)")


def fetch_macro_indicator_handler(indicator: str, **kwargs) -> str:
    """Fetch macro economic indicator. Supported: pmi, cpi, ppi, m2, social_financing."""
    import akshare as ak
    _rate_limit()
    try:
        if indicator == "pmi":
            df = ak.macro_china_pmi()
        elif indicator == "cpi":
            df = ak.macro_china_cpi_monthly()
        elif indicator == "ppi":
            df = ak.macro_china_ppi()
        elif indicator == "m2":
            df = ak.macro_china_money_supply()
        elif indicator == "social_financing":
            df = ak.macro_china_shrzgm()
        else:
            return _error_response(f"Unknown indicator: {indicator}", "Supported: pmi, cpi, ppi, m2, social_financing")

        if df is None or df.empty:
            return _error_response(f"No data for {indicator}")

        records = df.head(24).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e))


# =============================================================================
# SHARED TOOLS (registered in investment-company, also usable by committee via quant-support)
# =============================================================================


def calculate_pe_percentile_handler(stock_code: str, years: int = 10, **kwargs) -> str:
    """Calculate where current PE sits in N-year historical range for a stock or index."""
    import akshare as ak
    import pandas as pd
    _rate_limit()
    try:
        # Get historical price using sina backend
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df is None or df.empty:
            return _error_response(f"No price data for {stock_code}")

        # Get EPS from financial data (sorted old→new, latest is last row)
        _rate_limit()
        try:
            fin = ak.stock_financial_abstract_ths(symbol=stock_code)
            if fin is not None and not fin.empty and "基本每股收益" in fin.columns:
                # Find the latest row with valid EPS (searching from end)
                latest_eps = None
                for i in range(len(fin) - 1, max(len(fin) - 5, -1), -1):
                    val = fin.iloc[i]["基本每股收益"]
                    if val and str(val) != "False":
                        try:
                            latest_eps = float(val)
                            break
                        except (ValueError, TypeError):
                            continue
                if latest_eps is None:
                    return _error_response("Cannot calculate PE: no valid EPS found in recent reports")
            else:
                return _error_response("Cannot calculate PE: EPS data unavailable")
        except Exception:
            return _error_response("Cannot calculate PE: financial data fetch failed")

        if latest_eps <= 0:
            return _error_response(f"EPS is negative ({latest_eps}), PE not meaningful for this stock")

        # Calculate historical PEs using weekly samples
        df["date"] = pd.to_datetime(df["date"])
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        df_period = df[df["date"] >= cutoff].copy()

        if len(df_period) < 50:
            return _error_response(f"Insufficient data: only {len(df_period)} days in {years}-year window")

        # Sample weekly for efficiency
        df_weekly = df_period.resample("W", on="date").last().dropna(subset=["close"])
        df_weekly["pe"] = df_weekly["close"] / latest_eps
        current_pe = df_weekly["pe"].iloc[-1]
        percentile = (df_weekly["pe"] < current_pe).mean() * 100

        result = {
            "stock_code": stock_code,
            "current_pe": round(current_pe, 2),
            "percentile": round(percentile, 1),
            "years": years,
            "pe_min": round(df_weekly["pe"].min(), 2),
            "pe_max": round(df_weekly["pe"].max(), 2),
            "pe_median": round(df_weekly["pe"].median(), 2),
            "interpretation": (
                "Extremely cheap (bottom 10%)" if percentile < 10
                else "Cheap (bottom 25%)" if percentile < 25
                else "Below average" if percentile < 50
                else "Above average" if percentile < 75
                else "Expensive (top 25%)" if percentile < 90
                else "Extremely expensive (top 10%)"
            ),
        }
        return _ok_response(result)
    except Exception as e:
        return _error_response(str(e))


# =============================================================================
# TOOL SCHEMA DEFINITIONS
# =============================================================================

FETCH_STOCK_FINANCIALS_SCHEMA = {
    "name": "fetch_stock_financials",
    "description": "Fetch financial data (income statement, balance sheet, cashflow, or key metrics) for an A-share stock. Returns recent quarterly/annual data.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code, e.g. '002415' for Hikvision, '600519' for Moutai"},
            "data_type": {"type": "string", "enum": ["metrics", "income", "balance", "cashflow"], "description": "Type of financial data. 'metrics' gives key ratios (EPS, ROE, revenue growth)"},
        },
        "required": ["stock_code"],
    },
}

FETCH_STOCK_PRICE_SCHEMA = {
    "name": "fetch_stock_price",
    "description": "Fetch historical OHLCV price data for an A-share stock. Prices are forward-adjusted (前复权).",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
            "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "description": "Data frequency"},
            "days": {"type": "integer", "description": "Number of recent data points to return (default 120)"},
        },
        "required": ["stock_code"],
    },
}

FETCH_STOCK_INFO_SCHEMA = {
    "name": "fetch_stock_info",
    "description": "Fetch basic info for an A-share stock: company name, industry, total market cap, PE, PB, etc.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
        },
        "required": ["stock_code"],
    },
}

FETCH_INDUSTRY_CONSTITUENTS_SCHEMA = {
    "name": "fetch_industry_constituents",
    "description": "Fetch list of stocks in a given industry sector (东方财富行业板块). Returns stock codes, names, prices, and market caps.",
    "parameters": {
        "type": "object",
        "properties": {
            "industry": {"type": "string", "description": "Industry name in Chinese, e.g. '半导体', '白酒', '光伏设备', '创新药'"},
        },
        "required": ["industry"],
    },
}

FETCH_MARKET_INDEX_SCHEMA = {
    "name": "fetch_market_index",
    "description": "Fetch index price data. Use for market-level analysis (overall market valuation, trend). NOT for individual stocks.",
    "parameters": {
        "type": "object",
        "properties": {
            "index_code": {"type": "string", "description": "Index code: '000300' (CSI300), '000001' (SSE Composite), '399006' (ChiNext), '000905' (CSI500), '000688' (STAR50)"},
            "days": {"type": "integer", "description": "Number of recent trading days to return (default 60)"},
        },
        "required": ["index_code"],
    },
}

FETCH_MACRO_INDICATOR_SCHEMA = {
    "name": "fetch_macro_indicator",
    "description": "Fetch China macro economic indicators for market season judgment. NOT for company analysis.",
    "parameters": {
        "type": "object",
        "properties": {
            "indicator": {"type": "string", "enum": ["pmi", "cpi", "ppi", "m2", "social_financing"], "description": "Macro indicator to fetch"},
        },
        "required": ["indicator"],
    },
}

CALCULATE_PE_PERCENTILE_SCHEMA = {
    "name": "calculate_pe_percentile",
    "description": "Calculate where a stock's current PE ratio sits in its N-year historical range. Returns percentile (0-100%), with 0% being cheapest historically.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
            "years": {"type": "integer", "description": "Historical lookback period in years (default 10)"},
        },
        "required": ["stock_code"],
    },
}


# =============================================================================
# TOOL LISTS FOR REGISTRATION
# =============================================================================

# Format: (name, schema, handler, description)
COMPANY_TOOLS = [
    ("fetch_stock_financials", FETCH_STOCK_FINANCIALS_SCHEMA, fetch_stock_financials_handler, "Fetch A-share stock financial data"),
    ("fetch_stock_price", FETCH_STOCK_PRICE_SCHEMA, fetch_stock_price_handler, "Fetch historical stock price data"),
    ("fetch_stock_info", FETCH_STOCK_INFO_SCHEMA, fetch_stock_info_handler, "Fetch stock basic information"),
    ("fetch_industry_constituents", FETCH_INDUSTRY_CONSTITUENTS_SCHEMA, fetch_industry_constituents_handler, "List stocks in an industry sector"),
]

MARKET_TOOLS = [
    ("fetch_market_index", FETCH_MARKET_INDEX_SCHEMA, fetch_market_index_handler, "Fetch market index data"),
    ("fetch_macro_indicator", FETCH_MACRO_INDICATOR_SCHEMA, fetch_macro_indicator_handler, "Fetch macro economic indicators"),
]

SHARED_TOOLS = [
    ("calculate_pe_percentile", CALCULATE_PE_PERCENTILE_SCHEMA, calculate_pe_percentile_handler, "Calculate PE percentile in history"),
]
