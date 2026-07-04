"""
audit/audit_log.py
Thin convenience wrapper around storage.database's audit functions, giving
the dashboard and CLI a single, readable entry point for governance actions
(Key Capability #5: human-in-the-loop adjustments with audit tracking).
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import storage.database as db
def override_claim_category(claim_id: str, new_category: str, actor: str, reason: str):
    db.apply_human_override("claim", claim_id, "matched_category", new_category, actor, reason)

def override_revenue_weight(allocation_id: str, new_weight: float, actor: str, reason: str):
    db.apply_human_override("revenue_allocation", allocation_id, "weight", new_weight, actor, reason)
    db.apply_human_override("revenue_allocation", allocation_id, "basis", "human_override", actor, reason)

def override_hero_ingredient(ingredient_id: str, is_hero: bool, actor: str, reason: str):
    db.apply_human_override("ingredient", ingredient_id, "is_hero", int(is_hero), actor, reason)

def get_full_audit_trail():
    return db.fetch_all("audit_log")

def get_entity_audit_trail(entity_id: str):
    return db.fetch_where("audit_log", entity_id=entity_id)
