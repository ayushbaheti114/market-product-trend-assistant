"""
storage/database.py
--------------------
SQLite persistence layer. Acts as the "centralized, queryable intelligence
layer" called for in the brief (replacing spreadsheets/slides/notes).

Every write that originates from an AI agent OR a human override is mirrored
into the audit_log table, giving traceability from insight -> source data
(Key Capability #4) and supporting human-in-the-loop governance
(Key Capability #5).
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Dict, Optional, Any

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    brand TEXT, name TEXT, sku TEXT,
    annual_revenue REAL, retailer TEXT,
    raw_source TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS product_images (
    image_id TEXT PRIMARY KEY,
    product_id TEXT, source_url TEXT, local_path TEXT,
    ocr_text TEXT, ingested_at TEXT
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    product_id TEXT, text TEXT, matched_category TEXT,
    confidence REAL, source_image_id TEXT, source_snippet TEXT,
    extraction_method TEXT
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id TEXT PRIMARY KEY,
    product_id TEXT, canonical_name TEXT, raw_mention TEXT,
    is_hero INTEGER, source_claim_id TEXT
);

CREATE TABLE IF NOT EXISTS revenue_allocations (
    allocation_id TEXT PRIMARY KEY,
    product_id TEXT, category TEXT, allocated_revenue REAL,
    weight REAL, basis TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    category TEXT PRIMARY KEY,
    keywords_json TEXT, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    entry_id TEXT PRIMARY KEY,
    entity_type TEXT, entity_id TEXT, action TEXT, actor TEXT,
    reason TEXT, before_json TEXT, after_json TEXT, timestamp TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Generic insert/query helpers
# ---------------------------------------------------------------------------
def _insert(table: str, row: Dict[str, Any]):
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    with get_conn() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )


def insert_product(product) -> None:
    from models import to_dict
    _insert("products", to_dict(product))


def insert_product_image(image) -> None:
    from models import to_dict
    _insert("product_images", to_dict(image))


def insert_claim(claim) -> None:
    from models import to_dict
    _insert("claims", to_dict(claim))


def insert_ingredient(ingredient) -> None:
    from models import to_dict
    d = to_dict(ingredient)
    d["is_hero"] = int(d["is_hero"])
    _insert("ingredients", d)


def insert_revenue_allocation(alloc) -> None:
    from models import to_dict
    _insert("revenue_allocations", to_dict(alloc))


def log_audit(entry) -> None:
    from models import to_dict
    d = to_dict(entry)
    before_val = d.pop("before", None)
    after_val = d.pop("after", None)
    d["before_json"] = json.dumps(before_val) if before_val is not None else None
    d["after_json"] = json.dumps(after_val) if after_val is not None else None
    _insert("audit_log", d)


def sync_categories():
    """Push config.BENEFIT_CATEGORIES into the DB and log the update.
    This is the mechanism by which manual curators update the taxonomy
    (Strategic Decision #1: categories stay under manual control)."""
    from models import AuditEntry, new_id
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_conn() as conn:
        for cat, spec in config.BENEFIT_CATEGORIES.items():
            conn.execute(
                "INSERT OR REPLACE INTO categories (category, keywords_json, updated_at) VALUES (?, ?, ?)",
                (cat, json.dumps(spec["keywords"]), now),
            )
    log_audit(AuditEntry(
        entry_id=new_id("audit"),
        entity_type="category_taxonomy",
        entity_id="ALL",
        action="category_update",
        actor="system:config_sync",
        reason="Synced BENEFIT_CATEGORIES from config.py (manual curation)",
    ))


# ---------------------------------------------------------------------------
# Query helpers used by the dashboard / orchestrator
# ---------------------------------------------------------------------------
def fetch_all(table: str) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        return [dict(r) for r in rows]


def fetch_where(table: str, **filters) -> List[Dict]:
    clause = " AND ".join([f"{k} = ?" for k in filters])
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {clause}", list(filters.values())
        ).fetchall()
        return [dict(r) for r in rows]


def category_revenue_summary() -> List[Dict]:
    """Aggregate allocated revenue by benefit category -- the core
    'market product trend' view the dashboard drills into."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT category,
                   COUNT(DISTINCT product_id) AS product_count,
                   SUM(allocated_revenue) AS total_revenue
            FROM revenue_allocations
            GROUP BY category
            ORDER BY total_revenue DESC
        """).fetchall()
        return [dict(r) for r in rows]


def product_trace(product_id: str) -> Dict:
    """Full traceability bundle for a single product: raw record, images,
    claims, ingredients, and revenue allocation -- insight back to source."""
    with get_conn() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        images = conn.execute(
            "SELECT * FROM product_images WHERE product_id = ?", (product_id,)
        ).fetchall()
        claims = conn.execute(
            "SELECT * FROM claims WHERE product_id = ?", (product_id,)
        ).fetchall()
        ingredients = conn.execute(
            "SELECT * FROM ingredients WHERE product_id = ?", (product_id,)
        ).fetchall()
        allocations = conn.execute(
            "SELECT * FROM revenue_allocations WHERE product_id = ?", (product_id,)
        ).fetchall()
        audit = conn.execute(
            "SELECT * FROM audit_log WHERE entity_id IN "
            "(SELECT claim_id FROM claims WHERE product_id = ?) "
            "OR entity_id = ?", (product_id, product_id)
        ).fetchall()

    return {
        "product": dict(product) if product else None,
        "images": [dict(r) for r in images],
        "claims": [dict(r) for r in claims],
        "ingredients": [dict(r) for r in ingredients],
        "revenue_allocations": [dict(r) for r in allocations],
        "audit_trail": [dict(r) for r in audit],
    }


def apply_human_override(entity_type: str, entity_id: str, field_name: str,
                          new_value: Any, actor: str, reason: str):
    """Generic human-in-the-loop override with full audit tracking
    (Key Capability #5)."""
    from models import AuditEntry, new_id

    table_map = {
        "claim": "claims",
        "revenue_allocation": "revenue_allocations",
        "ingredient": "ingredients",
    }
    id_col_map = {
        "claim": "claim_id",
        "revenue_allocation": "allocation_id",
        "ingredient": "ingredient_id",
    }
    table = table_map[entity_type]
    id_col = id_col_map[entity_type]

    with get_conn() as conn:
        before_row = conn.execute(
            f"SELECT * FROM {table} WHERE {id_col} = ?", (entity_id,)
        ).fetchone()
        before = dict(before_row) if before_row else None

        conn.execute(
            f"UPDATE {table} SET {field_name} = ? WHERE {id_col} = ?",
            (new_value, entity_id),
        )

        after_row = conn.execute(
            f"SELECT * FROM {table} WHERE {id_col} = ?", (entity_id,)
        ).fetchone()
        after = dict(after_row) if after_row else None

    log_audit(AuditEntry(
        entry_id=new_id("audit"),
        entity_type=entity_type,
        entity_id=entity_id,
        action="human_override",
        actor=actor,
        reason=reason,
        before=before,
        after=after,
    ))
