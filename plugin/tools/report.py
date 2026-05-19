"""
Report generation and saving tools.

Saves research reports to a structured directory:
  ~/Documents/investment/reports/<sector>/<type>/YYYY-MM-DD_<code>_<name>.md
"""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any


_REPORTS_DIR = Path.home() / "Documents" / "investment" / "reports"


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def save_report_handler(args: dict, **kwargs) -> str:
    """Save a research report to the standard directory structure."""
    sector = args.get("sector", "tech")
    report_type = args.get("report_type", "deep")
    stock_code = args.get("stock_code", "unknown")
    stock_name = args.get("stock_name", "")
    content = args.get("content", "")

    if not content:
        return _safe_json({"status": "error", "error": "Report content is empty"})

    # Build path
    type_dir = _REPORTS_DIR / sector / report_type
    type_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    filename = f"{today}_{stock_code}"
    if stock_name:
        filename += f"_{stock_name}"
    filename += ".md"

    filepath = type_dir / filename

    # Write report
    filepath.write_text(content, encoding="utf-8")

    return _safe_json({
        "status": "ok",
        "path": str(filepath),
        "filename": filename,
    })


def list_reports_handler(args: dict, **kwargs) -> str:
    """List existing reports, optionally filtered by sector and type."""
    sector = args.get("sector", None)
    report_type = args.get("report_type", None)
    stock_code = args.get("stock_code", None)
    limit = int(args.get("limit", 20))

    try:
        results = []

        if sector:
            search_dirs = [_REPORTS_DIR / sector]
        else:
            search_dirs = [d for d in _REPORTS_DIR.iterdir() if d.is_dir()]

        for sector_dir in search_dirs:
            if not sector_dir.exists():
                continue
            type_dirs = [sector_dir / report_type] if report_type else [d for d in sector_dir.iterdir() if d.is_dir()]
            for type_dir in type_dirs:
                if not type_dir.exists():
                    continue
                for f in sorted(type_dir.glob("*.md"), reverse=True):
                    if stock_code and stock_code not in f.name:
                        continue
                    results.append({
                        "sector": sector_dir.name,
                        "type": type_dir.name,
                        "filename": f.name,
                        "path": str(f),
                        "size_kb": round(f.stat().st_size / 1024, 1),
                    })
                    if len(results) >= limit:
                        break

        return _safe_json({"status": "ok", "count": len(results), "reports": results})
    except Exception as e:
        return _safe_json({"status": "error", "error": str(e)})


# =============================================================================
# SCHEMAS
# =============================================================================

SAVE_REPORT_SCHEMA = {
    "name": "save_report",
    "description": "Save a research report (deep research, tracking, or framework) to the standardized reports directory. Use after completing analysis.",
    "parameters": {
        "type": "object",
        "properties": {
            "sector": {"type": "string", "enum": ["tech", "consumer", "pharma", "cyclical", "high_dividend"], "description": "Industry sector"},
            "report_type": {"type": "string", "enum": ["deep", "tracking", "framework"], "description": "Report type: deep=full research, tracking=monthly update, framework=industry overview"},
            "stock_code": {"type": "string", "description": "Stock code (e.g. '002415', '00700')"},
            "stock_name": {"type": "string", "description": "Company name (for filename)"},
            "content": {"type": "string", "description": "Full report content in Markdown format"},
        },
        "required": ["sector", "report_type", "stock_code", "content"],
    },
}

LIST_REPORTS_SCHEMA = {
    "name": "list_reports",
    "description": "List existing research reports. Can filter by sector, type, or stock code. Returns most recent reports first.",
    "parameters": {
        "type": "object",
        "properties": {
            "sector": {"type": "string", "enum": ["tech", "consumer", "pharma", "cyclical", "high_dividend"]},
            "report_type": {"type": "string", "enum": ["deep", "tracking", "framework"]},
            "stock_code": {"type": "string", "description": "Filter by stock code"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
    },
}

# =============================================================================
# TOOL LISTS FOR REGISTRATION
# =============================================================================

REPORT_TOOLS = [
    ("save_report", SAVE_REPORT_SCHEMA, save_report_handler, "Save research report to file"),
    ("list_reports", LIST_REPORTS_SCHEMA, list_reports_handler, "List existing research reports"),
]
