"""
models.py
---------
Lightweight dataclasses describing the core entities that flow through the
pipeline. Kept framework-agnostic (no ORM) so they serialize cleanly to
SQLite rows, JSON for the dashboard, and audit log payloads.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class ProductImage:
    image_id: str
    product_id: str
    source_url: Optional[str]
    local_path: Optional[str]
    ocr_text: str = ""
    ingested_at: str = field(default_factory=_now)


@dataclass
class Claim:
    claim_id: str
    product_id: str
    text: str
    matched_category: Optional[str] = None
    confidence: float = 0.0
    source_image_id: Optional[str] = None       # traceability
    source_snippet: str = ""                     # exact text the claim came from
    extraction_method: str = "rule_based"         # rule_based | llm | human_override


@dataclass
class Ingredient:
    ingredient_id: str
    product_id: str
    canonical_name: str
    raw_mention: str
    is_hero: bool = False                         # top-billed / most emphasized
    source_claim_id: Optional[str] = None


@dataclass
class RevenueAllocation:
    allocation_id: str
    product_id: str
    category: str
    allocated_revenue: float
    weight: float                                 # 0-1, share of product revenue
    basis: str = "claim_weighted"                  # claim_weighted | human_override


@dataclass
class Product:
    product_id: str
    brand: str
    name: str
    sku: str
    annual_revenue: float
    retailer: str = ""
    raw_source: str = "manual_upload"              # manual_upload | scraped
    created_at: str = field(default_factory=_now)


@dataclass
class AuditEntry:
    entry_id: str
    entity_type: str        # e.g. "claim", "category_assignment", "revenue_allocation"
    entity_id: str
    action: str              # "ai_generated" | "human_override" | "category_update"
    actor: str               # "system" or a user identifier
    reason: str = ""
    before: Optional[Dict] = None
    after: Optional[Dict] = None
    timestamp: str = field(default_factory=_now)


def new_id(kind: str) -> str:
    return _uid(kind)


def to_dict(obj) -> Dict:
    return asdict(obj)
