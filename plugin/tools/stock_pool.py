"""
Stock Pool tools - Expose the stock pool database to agents.

Registered in investment-company toolset (research agents can add/update stocks).
stock_pool_list and stock_pool_summary registered in both toolsets (coordinator needs access).
"""

import json
from typing import Any

from ..db.stock_pool import (
    add_stock, update_stock, get_stock, query_stocks, tier_summary,
    add_great_score, get_tracking_log, add_decision,
)


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


# =============================================================================
# HANDLERS
# =============================================================================

def stock_pool_add_handler(args: dict, **kwargs) -> str:
    """Add a stock to the pool."""
    try:
        result = add_stock(**args)
        return _safe_json(result)
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_update_handler(args: dict, **kwargs) -> str:
    """Update a stock's fields."""
    try:
        code = args.pop("code")
        market = args.pop("market", "A")
        result = update_stock(code, market, **args)
        return _safe_json(result)
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_get_handler(args: dict, **kwargs) -> str:
    """Get full details for one stock."""
    try:
        code = args.get("code", "")
        market = args.get("market", "A")
        result = get_stock(code, market)
        if result is None:
            return _safe_json({"status": "error", "error": f"Stock {code} ({market}) not found in pool"})
        return _safe_json({"status": "ok", "data": result})
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_query_handler(args: dict, **kwargs) -> str:
    """Query stocks by sector, tier, phase, etc."""
    try:
        results = query_stocks(**args)
        return _safe_json({"status": "ok", "count": len(results), "data": results})
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_summary_handler(args: dict, **kwargs) -> str:
    """Get summary counts by sector and tier."""
    try:
        results = tier_summary()
        return _safe_json({"status": "ok", "data": results})
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_great_score_handler(args: dict, **kwargs) -> str:
    """Record a GREAT score for a stock."""
    try:
        notes = {}
        for key in ["growth_note", "replicable_note", "potential_note", "excellent_note", "return_note"]:
            if key in args:
                notes[key.replace("_note", "")] = args.pop(key)
        args["notes"] = notes if notes else None
        result = add_great_score(**args)
        return _safe_json(result)
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def stock_pool_log_handler(args: dict, **kwargs) -> str:
    """Get tracking log for a stock."""
    try:
        code = args.get("code", "")
        market = args.get("market", "A")
        limit = int(args.get("limit", 20))
        results = get_tracking_log(code, market, limit)
        return _safe_json({"status": "ok", "count": len(results), "data": results})
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


def decision_log_add_handler(args: dict, **kwargs) -> str:
    """Record an investment decision."""
    try:
        result = add_decision(**args)
        return _safe_json(result)
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


# =============================================================================
# SCHEMAS
# =============================================================================

STOCK_POOL_ADD_SCHEMA = {
    "name": "stock_pool_add",
    "description": "Add a stock to the research pool. Use after completing initial research on a company. Specify sector, tier, and company type.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code (e.g. '002415' for A-share, '00700' for HK)"},
            "name": {"type": "string", "description": "Company name in Chinese"},
            "market": {"type": "string", "enum": ["A", "HK", "US"], "description": "Market (default: A)"},
            "sector": {"type": "string", "enum": ["tech", "consumer", "pharma", "cyclical", "high_dividend"], "description": "Industry sector"},
            "pool_tier": {"type": "string", "enum": ["core", "satellite", "watch", "reserve"], "description": "Pool tier (default: reserve)"},
            "company_type": {"type": "string", "enum": ["tree", "grain", "vegetable"], "description": "Tree=long-term compounder, Grain=cyclical growth, Vegetable=trading only"},
            "one_line_thesis": {"type": "string", "description": "One sentence: why is this stock worth tracking?"},
            "buy_company_test": {"type": "string", "description": "Would you buy the whole company at this price? Why?"},
        },
        "required": ["code", "name", "sector"],
    },
}

STOCK_POOL_UPDATE_SCHEMA = {
    "name": "stock_pool_update",
    "description": "Update fields of a stock already in the pool. Use to change tier, phase, rating, or other attributes. Important changes are automatically logged.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code"},
            "market": {"type": "string", "enum": ["A", "HK", "US"], "description": "Market (default: A)"},
            "pool_tier": {"type": "string", "enum": ["core", "satellite", "watch", "reserve"]},
            "build_phase": {"type": "string", "enum": ["phase0", "phase1", "phase2", "phase3"]},
            "rating": {"type": "string", "enum": ["strong_buy", "buy", "accumulate", "neutral", "reduce", "sell"]},
            "price_value_state": {"type": "string", "enum": ["no_reaction", "reasonable", "over_optimistic", "over_pessimistic"]},
            "company_type": {"type": "string", "enum": ["tree", "grain", "vegetable"]},
            "reason": {"type": "string", "description": "Reason for this change (required for audit trail)"},
        },
        "required": ["code", "reason"],
    },
}

STOCK_POOL_GET_SCHEMA = {
    "name": "stock_pool_get",
    "description": "Get full details for a stock in the pool, including latest GREAT score.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code"},
            "market": {"type": "string", "enum": ["A", "HK", "US"], "description": "Market (default: A)"},
        },
        "required": ["code"],
    },
}

STOCK_POOL_QUERY_SCHEMA = {
    "name": "stock_pool_query",
    "description": "Query stocks in the pool by filters. Returns list of matching stocks sorted by GREAT score.",
    "parameters": {
        "type": "object",
        "properties": {
            "sector": {"type": "string", "enum": ["tech", "consumer", "pharma", "cyclical", "high_dividend"]},
            "pool_tier": {"type": "string", "enum": ["core", "satellite", "watch", "reserve"]},
            "build_phase": {"type": "string", "enum": ["phase0", "phase1", "phase2", "phase3"]},
            "market": {"type": "string", "enum": ["A", "HK", "US"]},
            "limit": {"type": "integer", "description": "Max results (default 50)"},
        },
    },
}

STOCK_POOL_SUMMARY_SCHEMA = {
    "name": "stock_pool_summary",
    "description": "Get summary statistics of the stock pool: count by sector and tier, average GREAT scores.",
    "parameters": {"type": "object", "properties": {}},
}

STOCK_POOL_GREAT_SCORE_SCHEMA = {
    "name": "stock_pool_great_score",
    "description": "Record a GREAT five-dimension score for a stock. The stock must already be in the pool. Scores are 1-10 per dimension.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code"},
            "market": {"type": "string", "enum": ["A", "HK", "US"], "description": "Market (default: A)"},
            "growth": {"type": "integer", "description": "Growth score 1-10"},
            "replicable": {"type": "integer", "description": "Replicability score 1-10"},
            "potential": {"type": "integer", "description": "Potential/space score 1-10"},
            "excellent": {"type": "integer", "description": "Management quality score 1-10"},
            "return_certainty": {"type": "integer", "description": "Return certainty score 1-10"},
            "growth_note": {"type": "string", "description": "Brief evidence for growth score"},
            "replicable_note": {"type": "string", "description": "Brief evidence for replicability score"},
            "potential_note": {"type": "string", "description": "Brief evidence for potential score"},
            "excellent_note": {"type": "string", "description": "Brief evidence for management score"},
            "return_note": {"type": "string", "description": "Brief evidence for return certainty score"},
        },
        "required": ["code", "market", "growth", "replicable", "potential", "excellent", "return_certainty"],
    },
}

STOCK_POOL_LOG_SCHEMA = {
    "name": "stock_pool_log",
    "description": "Get the tracking log (change history) for a stock in the pool.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code"},
            "market": {"type": "string", "enum": ["A", "HK", "US"]},
            "limit": {"type": "integer", "description": "Max log entries (default 20)"},
        },
        "required": ["code"],
    },
}

DECISION_LOG_ADD_SCHEMA = {
    "name": "decision_log_add",
    "description": "Record an investment decision for the decision log. Used by the fund manager to document buy/sell/adjust decisions with rationale.",
    "parameters": {
        "type": "object",
        "properties": {
            "decision_type": {"type": "string", "enum": ["buy", "add", "reduce", "sell", "pool_change", "phase_advance"], "description": "Type of decision"},
            "stock_code": {"type": "string"},
            "stock_market": {"type": "string", "enum": ["A", "HK", "US"]},
            "content": {"type": "string", "description": "What was decided"},
            "rationale": {"type": "string", "description": "Why (the reasoning at time of decision)"},
            "build_phase": {"type": "string"},
            "expected_outcome": {"type": "string", "description": "What you expect to happen"},
            "review_date": {"type": "string", "description": "When to review (YYYY-MM-DD)"},
        },
        "required": ["decision_type", "content", "rationale"],
    },
}


# =============================================================================
# TOOL LISTS FOR REGISTRATION
# =============================================================================

POOL_COMPANY_TOOLS = [
    ("stock_pool_add", STOCK_POOL_ADD_SCHEMA, stock_pool_add_handler, "Add stock to research pool"),
    ("stock_pool_update", STOCK_POOL_UPDATE_SCHEMA, stock_pool_update_handler, "Update stock in pool"),
    ("stock_pool_get", STOCK_POOL_GET_SCHEMA, stock_pool_get_handler, "Get stock details from pool"),
    ("stock_pool_query", STOCK_POOL_QUERY_SCHEMA, stock_pool_query_handler, "Query stocks in pool"),
    ("stock_pool_great_score", STOCK_POOL_GREAT_SCORE_SCHEMA, stock_pool_great_score_handler, "Record GREAT score"),
    ("stock_pool_log", STOCK_POOL_LOG_SCHEMA, stock_pool_log_handler, "Get stock tracking log"),
    ("decision_log_add", DECISION_LOG_ADD_SCHEMA, decision_log_add_handler, "Record investment decision"),
]

POOL_SHARED_TOOLS = [
    ("stock_pool_summary", STOCK_POOL_SUMMARY_SCHEMA, stock_pool_summary_handler, "Get pool summary statistics"),
]
