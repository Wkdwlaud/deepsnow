"""
Stock Pool Database - SQLite backend for investment research persistence.

Provides CRUD operations for the stock pool, GREAT scores, tracking log,
and decision log. Auto-initializes the database on first use.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

_DB_DIR = Path.home() / ".hermes" / "investment-data"
_DB_PATH = _DB_DIR / "stock_pool.db"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _get_connection() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Auto-initialize schema
    if not _table_exists(conn, "stocks"):
        conn.executescript(_SCHEMA_PATH.read_text())
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row else {}


def _rows_to_list(rows) -> list:
    return [dict(r) for r in rows]


# =============================================================================
# Stock CRUD
# =============================================================================

def add_stock(
    code: str, name: str, market: str = "A", sector: str = "tech",
    pool_tier: str = "reserve", company_type: str = None,
    build_phase: str = "phase0", **kwargs
) -> dict:
    conn = _get_connection()
    try:
        fields = {
            "code": code, "name": name, "market": market, "sector": sector,
            "pool_tier": pool_tier, "company_type": company_type,
            "build_phase": build_phase,
        }
        for k in ["business_model", "industry_cycle", "price_value_state",
                  "consensus_stage", "rating", "great_total",
                  "target_price_conservative", "target_price_neutral",
                  "target_price_optimistic", "buy_company_test",
                  "one_line_thesis", "tracking_points", "sell_signals", "notes"]:
            if k in kwargs:
                fields[k] = kwargs[k]

        cols = ", ".join(fields.keys())
        placeholders = ", ".join(["?"] * len(fields))
        conn.execute(f"INSERT OR REPLACE INTO stocks ({cols}) VALUES ({placeholders})", list(fields.values()))
        conn.commit()

        # Log the addition
        _add_tracking_log(conn, code, market, "tier_change", None, pool_tier, f"Added to {pool_tier} pool")
        return {"status": "ok", "action": "added", "code": code, "market": market, "tier": pool_tier}
    finally:
        conn.close()


def update_stock(code: str, market: str = "A", **updates) -> dict:
    conn = _get_connection()
    try:
        # Check stock exists
        cur = conn.execute("SELECT * FROM stocks WHERE code=? AND market=?", (code, market))
        existing = cur.fetchone()
        if not existing:
            return {"status": "error", "error": f"Stock {code} ({market}) not found in pool"}

        # Track important field changes
        track_fields = ["pool_tier", "build_phase", "rating", "price_value_state", "consensus_stage"]
        for field in track_fields:
            if field in updates and updates[field] != existing[field]:
                reason = updates.pop("reason", f"Updated {field}")
                _add_tracking_log(conn, code, market, f"{field}_change" if "_" not in field else field.replace("_", "_") + "_change",
                                  existing[field], updates[field], reason)

        if updates:
            updates["updated_at"] = "datetime('now')"
            set_clause = ", ".join([f"{k}=?" for k in updates.keys() if k != "updated_at"])
            set_clause += ", updated_at=datetime('now')"
            values = [v for k, v in updates.items() if k != "updated_at"]
            conn.execute(f"UPDATE stocks SET {set_clause} WHERE code=? AND market=?", values + [code, market])
            conn.commit()

        return {"status": "ok", "action": "updated", "code": code, "fields": list(updates.keys())}
    finally:
        conn.close()


def get_stock(code: str, market: str = "A") -> Optional[dict]:
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM stocks WHERE code=? AND market=?", (code, market))
        row = cur.fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        # Also fetch latest GREAT score
        cur2 = conn.execute(
            "SELECT * FROM great_scores WHERE stock_code=? AND stock_market=? ORDER BY scored_at DESC LIMIT 1",
            (code, market)
        )
        great = cur2.fetchone()
        if great:
            result["latest_great"] = _row_to_dict(great)
        return result
    finally:
        conn.close()


def query_stocks(sector: str = None, pool_tier: str = None, build_phase: str = None,
                 market: str = None, limit: int = 50) -> list:
    conn = _get_connection()
    try:
        conditions = []
        params = []
        if sector:
            conditions.append("sector=?")
            params.append(sector)
        if pool_tier:
            conditions.append("pool_tier=?")
            params.append(pool_tier)
        if build_phase:
            conditions.append("build_phase=?")
            params.append(build_phase)
        if market:
            conditions.append("market=?")
            params.append(market)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        cur = conn.execute(f"SELECT * FROM stocks{where} ORDER BY great_total DESC NULLS LAST LIMIT ?", params + [limit])
        return _rows_to_list(cur.fetchall())
    finally:
        conn.close()


def tier_summary() -> list:
    conn = _get_connection()
    try:
        cur = conn.execute("""
            SELECT sector, pool_tier, COUNT(*) as count, AVG(great_total) as avg_great
            FROM stocks GROUP BY sector, pool_tier ORDER BY sector, pool_tier
        """)
        return _rows_to_list(cur.fetchall())
    finally:
        conn.close()


# =============================================================================
# GREAT Scores
# =============================================================================

def add_great_score(code: str, market: str, growth: int, replicable: int,
                    potential: int, excellent: int, return_certainty: int,
                    notes: dict = None) -> dict:
    conn = _get_connection()
    try:
        params = {
            "stock_code": code, "stock_market": market,
            "growth": growth, "replicable": replicable,
            "potential": potential, "excellent": excellent,
            "return_certainty": return_certainty,
        }
        if notes:
            params["growth_note"] = notes.get("growth", "")
            params["replicable_note"] = notes.get("replicable", "")
            params["potential_note"] = notes.get("potential", "")
            params["excellent_note"] = notes.get("excellent", "")
            params["return_note"] = notes.get("return_certainty", "")

        cols = ", ".join(params.keys())
        placeholders = ", ".join(["?"] * len(params))
        conn.execute(f"INSERT INTO great_scores ({cols}) VALUES ({placeholders})", list(params.values()))

        # Update total in stocks table
        total = growth + replicable + potential + excellent + return_certainty
        conn.execute("UPDATE stocks SET great_total=?, updated_at=datetime('now') WHERE code=? AND market=?",
                     (total, code, market))
        conn.commit()

        _add_tracking_log(conn, code, market, "great_update", None, str(total), f"GREAT score updated: G{growth}/R{replicable}/P{potential}/E{excellent}/T{return_certainty}={total}")
        return {"status": "ok", "total": total}
    finally:
        conn.close()


# =============================================================================
# Tracking Log
# =============================================================================

def _add_tracking_log(conn: sqlite3.Connection, code: str, market: str,
                      event_type: str, old_value: str, new_value: str, reason: str):
    conn.execute(
        "INSERT INTO tracking_log (stock_code, stock_market, event_type, old_value, new_value, reason) VALUES (?,?,?,?,?,?)",
        (code, market, event_type, old_value, new_value, reason)
    )
    conn.commit()


def get_tracking_log(code: str, market: str = "A", limit: int = 20) -> list:
    conn = _get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM tracking_log WHERE stock_code=? AND stock_market=? ORDER BY logged_at DESC LIMIT ?",
            (code, market, limit)
        )
        return _rows_to_list(cur.fetchall())
    finally:
        conn.close()


# =============================================================================
# Decision Log
# =============================================================================

def add_decision(decision_type: str, content: str, rationale: str,
                 stock_code: str = None, stock_market: str = None,
                 build_phase: str = None, expected_outcome: str = None,
                 review_date: str = None, data_snapshot: dict = None) -> dict:
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO decision_log
            (decision_type, stock_code, stock_market, content, build_phase, rationale,
             data_snapshot, expected_outcome, review_date)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (decision_type, stock_code, stock_market, content, build_phase, rationale,
             json.dumps(data_snapshot) if data_snapshot else None,
             expected_outcome, review_date)
        )
        conn.commit()
        return {"status": "ok", "action": "decision_logged"}
    finally:
        conn.close()
