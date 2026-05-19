"""
Financial data tools wrapping akshare for A-share market data.

Tools are organized into three categories:
- COMPANY_TOOLS: Individual stock data (registered in investment-company toolset)
- MARKET_TOOLS: Market/index/macro data (registered in investment-market toolset)
- SHARED_TOOLS: Cross-cutting quant data (registered in both toolsets)

IMPORTANT: Hermes dispatches tool handlers as handler(args_dict, **kwargs).
The first argument is always the full parameters dict, NOT individual params.
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


def fetch_stock_financials_handler(args: dict, **kwargs) -> str:
    """Fetch financial data for an A-share stock."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    data_type = args.get("data_type", "metrics")
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

        records = df.tail(20).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Check stock code (6 digits, e.g. 002415) or try again later")


def fetch_stock_price_handler(args: dict, **kwargs) -> str:
    """Fetch historical price data for an A-share stock."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    days = int(args.get("days", 120))
    _rate_limit()
    try:
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df is None or df.empty:
            return _error_response(f"No price data for {stock_code}")

        records = df.tail(days).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Check stock code format (6 digits) or try again")


def fetch_stock_info_handler(args: dict, **kwargs) -> str:
    """Fetch basic information for an A-share stock."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    _rate_limit()
    try:
        info = {"stock_code": stock_code}

        prefix = "sh" if stock_code.startswith("6") else "sz"
        df_price = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df_price is not None and not df_price.empty:
            latest = df_price.iloc[-1]
            info["latest_price"] = float(latest["close"])
            info["latest_date"] = str(latest["date"])
            info["volume"] = int(latest["volume"])

        _rate_limit()
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


def fetch_industry_constituents_handler(args: dict, **kwargs) -> str:
    """Fetch list of stocks in a given industry sector."""
    import akshare as ak
    industry = args.get("industry", "")
    _rate_limit()
    try:
        try:
            df = ak.stock_board_industry_cons_em(symbol=industry)
            if df is not None and not df.empty:
                cols = ["代码", "名称", "最新价", "涨跌幅", "总市值"]
                available_cols = [c for c in cols if c in df.columns]
                records = df[available_cols].head(50).to_dict(orient="records")
                return _ok_response(records)
        except Exception:
            pass

        _rate_limit()
        try:
            df_summary = ak.stock_board_industry_summary_ths()
            if df_summary is not None and not df_summary.empty:
                match = df_summary[df_summary["板块"].str.contains(industry, na=False)]
                if not match.empty:
                    records = match.head(5).to_dict(orient="records")
                    return _ok_response({"note": "Detailed constituents unavailable, showing industry summary", "data": records})
        except Exception:
            pass

        return _error_response(
            f"Cannot fetch constituents for '{industry}'",
            "Use Chinese industry name, e.g. '半导体', '白酒', '光伏设备'"
        )
    except Exception as e:
        return _error_response(str(e))


# =============================================================================
# MARKET-LEVEL TOOLS (investment-market toolset)
# =============================================================================


def fetch_market_index_handler(args: dict, **kwargs) -> str:
    """Fetch index data. Common indices: 000300 (CSI300), 000001 (SSE), 399006 (ChiNext)."""
    import akshare as ak
    index_code = args.get("index_code", "000300")
    days = int(args.get("days", 60))
    _rate_limit()
    try:
        df = ak.stock_zh_index_daily(symbol=f"sh{index_code}" if index_code.startswith("0") else f"sz{index_code}")
        if df is None or df.empty:
            return _error_response(f"No data for index {index_code}")

        records = df.tail(days).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Common indices: 000300 (CSI300), 000001 (SSE), 399006 (ChiNext)")


def fetch_macro_indicator_handler(args: dict, **kwargs) -> str:
    """Fetch macro economic indicator. Supported: pmi, cpi, ppi, m2, social_financing."""
    import akshare as ak
    indicator = args.get("indicator", "")
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
# SHARED TOOLS (registered in investment-company toolset)
# =============================================================================


def calculate_pe_percentile_handler(args: dict, **kwargs) -> str:
    """Calculate where current PE sits in N-year historical range for a stock."""
    import akshare as ak
    import pandas as pd
    stock_code = args.get("stock_code", "")
    years = int(args.get("years", 10))
    _rate_limit()
    try:
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df is None or df.empty:
            return _error_response(f"No price data for {stock_code}")

        _rate_limit()
        try:
            fin = ak.stock_financial_abstract_ths(symbol=stock_code)
            if fin is not None and not fin.empty and "基本每股收益" in fin.columns:
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

        df["date"] = pd.to_datetime(df["date"])
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        df_period = df[df["date"] >= cutoff].copy()

        if len(df_period) < 50:
            return _error_response(f"Insufficient data: only {len(df_period)} days in {years}-year window")

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


def calculate_forward_peg_handler(args: dict, **kwargs) -> str:
    """Calculate Forward PEG using analyst consensus EPS forecasts."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    _rate_limit()
    try:
        # Get consensus EPS forecasts
        df_forecast = ak.stock_profit_forecast_ths(symbol=stock_code)
        if df_forecast is None or df_forecast.empty:
            return _error_response(f"No analyst forecast data for {stock_code}", "This stock may not have enough analyst coverage")

        # Get current price
        _rate_limit()
        prefix = "sh" if stock_code.startswith("6") else "sz"
        df_price = ak.stock_zh_a_daily(symbol=f"{prefix}{stock_code}", adjust="qfq")
        if df_price is None or df_price.empty:
            return _error_response(f"No price data for {stock_code}")

        current_price = float(df_price.iloc[-1]["close"])

        # Parse forecast data
        forecasts = []
        for _, row in df_forecast.iterrows():
            forecasts.append({
                "year": str(row["年度"]),
                "analyst_count": int(row["预测机构数"]),
                "eps_min": float(row["最小值"]),
                "eps_mean": float(row["均值"]),
                "eps_max": float(row["最大值"]),
            })

        if len(forecasts) < 2:
            return _error_response("Need at least 2 years of forecast data to calculate growth rate")

        # Calculate Forward PE (using nearest year consensus EPS)
        eps_y1 = forecasts[0]["eps_mean"]
        forward_pe = current_price / eps_y1 if eps_y1 > 0 else None

        # Calculate 3-year EPS CAGR
        eps_first = forecasts[0]["eps_mean"]
        eps_last = forecasts[-1]["eps_mean"]
        n_years = len(forecasts) - 1
        if eps_first > 0 and eps_last > eps_first:
            cagr = ((eps_last / eps_first) ** (1 / n_years) - 1) * 100
        elif eps_first > 0:
            cagr = ((eps_last / eps_first) ** (1 / n_years) - 1) * 100
        else:
            cagr = None

        # Calculate Forward PEG
        forward_peg = forward_pe / cagr if (forward_pe and cagr and cagr > 0) else None

        result = {
            "stock_code": stock_code,
            "current_price": round(current_price, 2),
            "forward_pe": round(forward_pe, 2) if forward_pe else None,
            "eps_cagr_pct": round(cagr, 1) if cagr else None,
            "forward_peg": round(forward_peg, 2) if forward_peg else None,
            "peg_interpretation": (
                "Significantly undervalued (PEG < 0.5)" if forward_peg and forward_peg < 0.5
                else "Attractive (PEG 0.5-0.8)" if forward_peg and forward_peg < 0.8
                else "Fair value (PEG 0.8-1.0)" if forward_peg and forward_peg < 1.0
                else "Slightly expensive (PEG 1.0-1.5)" if forward_peg and forward_peg < 1.5
                else "Expensive (PEG > 1.5)" if forward_peg and forward_peg >= 1.5
                else "Cannot calculate (negative growth)"
            ),
            "forecast_years": len(forecasts),
            "analyst_count": forecasts[0]["analyst_count"],
            "forecasts": forecasts,
        }
        return _ok_response(result)
    except Exception as e:
        return _error_response(str(e))


# =============================================================================
# HK STOCK TOOLS (investment-company toolset)
# =============================================================================


def fetch_hk_stock_price_handler(args: dict, **kwargs) -> str:
    """Fetch historical price data for a Hong Kong listed stock."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    days = int(args.get("days", 120))
    _rate_limit()
    try:
        # Try eastmoney backend first, fallback to sina
        try:
            df = ak.stock_hk_hist(symbol=stock_code, period="daily", adjust="qfq")
        except Exception:
            _rate_limit()
            df = ak.stock_hk_daily(symbol=stock_code, adjust="qfq")
        if df is None or df.empty:
            return _error_response(f"No price data for HK:{stock_code}")

        records = df.tail(days).to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Use 5-digit HK stock code, e.g. '00700' for Tencent, '09988' for Alibaba")


def fetch_hk_stock_info_handler(args: dict, **kwargs) -> str:
    """Fetch basic info and financial indicators for a HK stock."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    _rate_limit()
    try:
        info = {"stock_code": stock_code, "market": "HK"}

        # Get latest price (try eastmoney, fallback to sina)
        try:
            df_price = ak.stock_hk_hist(symbol=stock_code, period="daily", adjust="qfq")
            if df_price is not None and not df_price.empty:
                latest = df_price.iloc[-1]
                info["latest_price_hkd"] = float(latest["收盘"])
                info["latest_date"] = str(latest["日期"])
                info["change_pct"] = float(latest["涨跌幅"])
                info["volume"] = int(latest["成交量"])
        except Exception:
            _rate_limit()
            try:
                df_price = ak.stock_hk_daily(symbol=stock_code, adjust="qfq")
                if df_price is not None and not df_price.empty:
                    latest = df_price.iloc[-1]
                    info["latest_price_hkd"] = float(latest["close"])
                    info["latest_date"] = str(latest["date"])
                    info["volume"] = int(latest["volume"])
            except Exception:
                pass

        # Get financial indicators
        _rate_limit()
        try:
            df_fin = ak.stock_hk_financial_indicator_em(symbol=stock_code)
            if df_fin is not None and not df_fin.empty:
                row = df_fin.iloc[0]
                info["eps"] = str(row.get("基本每股收益(元)", ""))
                info["nav_per_share"] = str(row.get("每股净资产(元)", ""))
                info["dividend_per_share_ttm"] = str(row.get("每股股息TTM(港元)", ""))
                info["dividend_yield_ttm"] = str(row.get("股息率TTM(%)", ""))
                info["shares_outstanding"] = str(row.get("已发行股本(股)", ""))
        except Exception:
            pass

        # Get company profile
        _rate_limit()
        try:
            df_profile = ak.stock_hk_company_profile_em(symbol=stock_code)
            if df_profile is not None and not df_profile.empty:
                row = df_profile.iloc[0]
                info["company_name"] = str(row.get("公司名称", ""))
                info["industry"] = str(row.get("所属行业", ""))
                info["chairman"] = str(row.get("董事长", ""))
                info["employees"] = str(row.get("员工人数", ""))
        except Exception:
            pass

        return _ok_response(info)
    except Exception as e:
        return _error_response(str(e), "Use 5-digit HK code, e.g. '00700' for Tencent")


def fetch_hk_stock_financials_handler(args: dict, **kwargs) -> str:
    """Fetch annual financial analysis indicators for a HK stock (ROE, margins, growth rates)."""
    import akshare as ak
    stock_code = args.get("stock_code", "")
    _rate_limit()
    try:
        df = ak.stock_financial_hk_analysis_indicator_em(symbol=stock_code)
        if df is None or df.empty:
            return _error_response(f"No financial data for HK:{stock_code}")

        # Select key columns
        key_cols = [
            "REPORT_DATE", "BASIC_EPS", "BPS", "OPERATE_INCOME",
            "OPERATE_INCOME_YOY", "HOLDER_PROFIT", "HOLDER_PROFIT_YOY",
            "GROSS_PROFIT_RATIO", "NET_PROFIT_RATIO", "ROE_AVG", "ROA",
            "DEBT_ASSET_RATIO", "CURRENT_RATIO"
        ]
        available_cols = [c for c in key_cols if c in df.columns]
        records = df[available_cols].to_dict(orient="records")
        return _ok_response(records)
    except Exception as e:
        return _error_response(str(e), "Use 5-digit HK code, e.g. '00700'")


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
    "description": "Fetch historical OHLCV price data for an A-share stock. Prices are forward-adjusted.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
            "days": {"type": "integer", "description": "Number of recent data points to return (default 120)"},
        },
        "required": ["stock_code"],
    },
}

FETCH_STOCK_INFO_SCHEMA = {
    "name": "fetch_stock_info",
    "description": "Fetch basic info for an A-share stock: latest price, EPS, revenue, profit growth, etc.",
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
    "description": "Fetch list of stocks in a given industry sector. Returns stock codes, names, prices, and market caps.",
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
    "description": "Fetch index price data. Use for market-level analysis. NOT for individual stocks.",
    "parameters": {
        "type": "object",
        "properties": {
            "index_code": {"type": "string", "description": "Index code: '000300' (CSI300), '000001' (SSE Composite), '399006' (ChiNext), '000905' (CSI500)"},
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
    "description": "Calculate where a stock's current PE ratio sits in its N-year historical range. Returns percentile (0-100%). A-share only.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
            "years": {"type": "integer", "description": "Historical lookback period in years (default 10)"},
        },
        "required": ["stock_code"],
    },
}

FETCH_HK_STOCK_PRICE_SCHEMA = {
    "name": "fetch_hk_stock_price",
    "description": "Fetch historical daily OHLCV data for a Hong Kong listed stock. Use for HK stocks like Tencent (00700), Alibaba (09988), Meituan (03690).",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "5-digit HK stock code, e.g. '00700' for Tencent, '09988' for Alibaba, '03690' for Meituan"},
            "days": {"type": "integer", "description": "Number of recent trading days to return (default 120)"},
        },
        "required": ["stock_code"],
    },
}

FETCH_HK_STOCK_INFO_SCHEMA = {
    "name": "fetch_hk_stock_info",
    "description": "Fetch basic info for a HK stock: price, EPS, dividend yield, company name, industry, employees. Use for HK-listed companies.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "5-digit HK stock code, e.g. '00700' for Tencent"},
        },
        "required": ["stock_code"],
    },
}

FETCH_HK_STOCK_FINANCIALS_SCHEMA = {
    "name": "fetch_hk_stock_financials",
    "description": "Fetch annual financial indicators for a HK stock: EPS, ROE, revenue growth, profit growth, margins, debt ratio. Returns multiple years for trend analysis.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "5-digit HK stock code, e.g. '00700' for Tencent"},
        },
        "required": ["stock_code"],
    },
}

CALCULATE_FORWARD_PEG_SCHEMA = {
    "name": "calculate_forward_peg",
    "description": "Calculate Forward PEG using analyst consensus EPS forecasts (同花顺一致预期). Returns Forward PE, EPS CAGR, Forward PEG, and full forecast breakdown. A-share only. Essential for growth stock valuation.",
    "parameters": {
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "6-digit A-share stock code"},
        },
        "required": ["stock_code"],
    },
}


# =============================================================================
# TOOL LISTS FOR REGISTRATION
# Format: (name, schema, handler, description)
# =============================================================================

COMPANY_TOOLS = [
    ("fetch_stock_financials", FETCH_STOCK_FINANCIALS_SCHEMA, fetch_stock_financials_handler, "Fetch A-share stock financial data"),
    ("fetch_stock_price", FETCH_STOCK_PRICE_SCHEMA, fetch_stock_price_handler, "Fetch historical stock price data"),
    ("fetch_stock_info", FETCH_STOCK_INFO_SCHEMA, fetch_stock_info_handler, "Fetch stock basic information"),
    ("fetch_industry_constituents", FETCH_INDUSTRY_CONSTITUENTS_SCHEMA, fetch_industry_constituents_handler, "List stocks in an industry sector"),
    ("calculate_forward_peg", CALCULATE_FORWARD_PEG_SCHEMA, calculate_forward_peg_handler, "Calculate Forward PEG from analyst consensus"),
    ("fetch_hk_stock_price", FETCH_HK_STOCK_PRICE_SCHEMA, fetch_hk_stock_price_handler, "Fetch HK stock historical price data"),
    ("fetch_hk_stock_info", FETCH_HK_STOCK_INFO_SCHEMA, fetch_hk_stock_info_handler, "Fetch HK stock basic information"),
    ("fetch_hk_stock_financials", FETCH_HK_STOCK_FINANCIALS_SCHEMA, fetch_hk_stock_financials_handler, "Fetch HK stock annual financial indicators"),
]

MARKET_TOOLS = [
    ("fetch_market_index", FETCH_MARKET_INDEX_SCHEMA, fetch_market_index_handler, "Fetch market index data"),
    ("fetch_macro_indicator", FETCH_MACRO_INDICATOR_SCHEMA, fetch_macro_indicator_handler, "Fetch macro economic indicators"),
]

SHARED_TOOLS = [
    ("calculate_pe_percentile", CALCULATE_PE_PERCENTILE_SCHEMA, calculate_pe_percentile_handler, "Calculate PE percentile in history"),
]
