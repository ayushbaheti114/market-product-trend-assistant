"""
agents/orchestrator.py
Orchestrator Agent.
Two responsibilities:
1. PIPELINE MODE (process_product): runs a single product through the full
   agent chain (Claims -> Ingredients -> Market Matching -> Revenue) and
   persists everything with audit logging. This is what "replicates the
   manual workflow" (Strategic Decision #3).

2. QUERY MODE (handle_query): a lightweight rule-based intent parser that
   powers the dashboard's conversational querying (Key Capability #1). It
   is intentionally simple/deterministic for the prototype -- swap in an
   LLM-based router later without changing the downstream agent contracts.
"""

import os
import re
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import storage.database as db
from agents.claims_agent import ProductClaimsAgent
from agents.ingredient_agent import HeroIngredientExtractorAgent
from agents.market_matching_agent import MarketMatchingAgent
from agents.revenue_agent import RevenueAttributionAgent
from agents.base import BaseAgent

class OrchestratorAgent(BaseAgent):
    name = "OrchestratorAgent"

    def __init__(self):
        self.claims_agent = ProductClaimsAgent()
        self.ingredient_agent = HeroIngredientExtractorAgent()
        self.market_agent = MarketMatchingAgent()
        self.revenue_agent = RevenueAttributionAgent()
       
    # Pipeline mode
    def process_product(self, product, image_path: str = None,
                         fallback_ocr_text: str = "", source_image_id: str = None):
        """Runs the full agent chain for one product and persists results.
        `product` is a models.Product already inserted into the DB."""
        self.log(f"Processing product {product.product_id} ({product.name})")
        full_text = self.claims_agent.ocr_image(image_path, fallback_ocr_text)
        claims = self.claims_agent.run(
            product_id=product.product_id,
            image_path=image_path,
            fallback_text=fallback_ocr_text,
            source_image_id=source_image_id,
        )
        for c in claims:
            db.insert_claim(c)
        ingredients = self.ingredient_agent.run(product.product_id, claims, full_ocr_text=full_text)
        for ing in ingredients:
            db.insert_ingredient(ing)
        category_weights = self.market_agent.run(claims)
        # write matched_category back onto claims for traceability
        for category, weight, claim_ids in category_weights:
            for cid in claim_ids:
                with db.get_conn() as conn:
                    conn.execute(
                        "UPDATE claims SET matched_category = ? WHERE claim_id = ?",
                        (category, cid),
                    )

        allocations = self.revenue_agent.run(
            product.product_id, product.annual_revenue, category_weights
        )
        for alloc in allocations:
            db.insert_revenue_allocation(alloc)

        from models import AuditEntry, new_id
        db.log_audit(AuditEntry(
            entry_id=new_id("audit"),
            entity_type="product",
            entity_id=product.product_id,
            action="ai_generated",
            actor="system:pipeline",
            reason="Full pipeline run: claims -> ingredients -> market match -> revenue allocation",
            after={"claims": len(claims), "ingredients": len(ingredients),
                   "allocations": len(allocations)},
        ))

        return {
            "product_id": product.product_id,
            "claims": claims,
            "ingredients": ingredients,
            "category_weights": category_weights,
            "allocations": allocations,
        }
                            
    # Query mode (conversational dashboard)
    def handle_query(self, prompt: str) -> dict:
        """Very lightweight intent router for natural-language dashboard
        queries. Returns a dict with 'intent', 'data', and 'explanation'
        so the UI can render both the answer and its provenance."""
        p = prompt.lower().strip()

        # Intent: top categories / trends
        if re.search(r"\b(top|leading|biggest|trend)\b", p) and "categor" in p:
            data = db.category_revenue_summary()
            return {
                "intent": "top_categories",
                "data": data,
                "explanation": "Ranked by total allocated revenue across all "
                                "processed products, summed from each product's "
                                "claim-weighted category allocations.",
            }

        # Intent: product lookup / traceability (checked before category
        # keyword matching, since an explicit "product <sku>" mention is
        # more specific than a loose category keyword match).
        prod_match = re.search(r"(?:product|sku)\s+([a-zA-Z0-9_\-]+)", p)
        if prod_match:
            pid_fragment = prod_match.group(1)
            all_products = db.fetch_all("products")
            candidates = [pr for pr in all_products
                          if pid_fragment.lower() in pr["product_id"].lower()
                          or pid_fragment.lower() in pr["sku"].lower()]
            if candidates:
                trace = db.product_trace(candidates[0]["product_id"])
                return {"intent": "product_trace", "data": trace,
                        "explanation": "Full traceability bundle: source image(s), "
                                        "extracted claims, ingredients, and revenue "
                                        "allocation for this product."}

        # Intent: drill down into a specific category. Matches if the full
        # category name appears in the prompt, OR if a significant word
        # from the category name (e.g. "sleep" from "Sleep & Relaxation")
        # appears in the prompt.
        cat_match = None
        stopwords = {"and", "&", "health", "support", "management"}
        for cat in db.fetch_all("categories"):
            cat_name = cat["category"].lower()
            if cat_name in p:
                cat_match = cat["category"]
                break
            words = [w for w in re.findall(r"[a-z]+", cat_name) if w not in stopwords and len(w) > 3]
            if words and any(w in p for w in words):
                cat_match = cat["category"]
                break
        if cat_match:
            rows = db.fetch_where("revenue_allocations", category=cat_match)
            return {
                "intent": "category_drilldown",
                "category": cat_match,
                "data": rows,
                "explanation": f"All revenue allocations tagged to '{cat_match}', "
                                f"traceable to the underlying claims via each "
                                f"allocation's product_id.",
            }

        # Intent: ingredient frequency
        if "ingredient" in p:
            ingredients = db.fetch_all("ingredients")
            from collections import Counter
            counts = Counter(i["canonical_name"] for i in ingredients)
            return {
                "intent": "ingredient_frequency",
                "data": sorted(counts.items(), key=lambda kv: -kv[1]),
                "explanation": "Frequency count of canonical ingredients "
                                "identified across all processed products.",
            }

        # Fallback: general summary
        products = db.fetch_all("products")
        summary = db.category_revenue_summary()
        return {
            "intent": "general_summary",
            "data": {"total_products": len(products), "category_summary": summary},
            "explanation": "Could not parse a specific intent; showing overall "
                            "portfolio summary. Try asking about 'top categories', "
                            "a specific category name, a product id, or 'ingredients'.",
        }
