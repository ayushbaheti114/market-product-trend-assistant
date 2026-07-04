"""
agents/market_matching_agent.py
Market Matching Agent.
Maps a product's claims to the MANUALLY CURATED benefit categories
(config.BENEFIT_CATEGORIES / storage.categories table) via weighted keyword
scoring. Categories themselves are never invented by this agent -- it only
scores against the existing taxonomy, per Strategic Decision
#1. Output is a normalized score per category (sums to 1.0 across matched
categories) which the Revenue Attribution Agent consumes directly as
allocation weights.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.base import BaseAgent

class MarketMatchingAgent(BaseAgent):
    name = "MarketMatchingAgent"
    def __init__(self, categories: dict = None):
        # categories: {category_name: {"keywords": {kw: weight}}}
        self.categories = categories or config.BENEFIT_CATEGORIES

    def score_text(self, text: str) -> dict:
        lowered = text.lower()
        raw_scores = {}
        for category, spec in self.categories.items():
            score = 0.0
            for kw, weight in spec["keywords"].items():
                if kw in lowered:
                    score += weight
            if score > 0:
                raw_scores[category] = score
        return raw_scores

    def run(self, claims):
        """claims: list of Claim objects (or dicts). Returns list of
        (category, normalized_weight, matched_claim_ids) sorted desc."""
        combined_text = " ".join(
            (c.text if hasattr(c, "text") else c.get("text", "")) for c in claims
        )
        raw_scores = self.score_text(combined_text)
        if not raw_scores:
            return [("Uncategorized", 1.0, [])]

        total = sum(raw_scores.values())
        results = []
        for category, score in sorted(raw_scores.items(), key=lambda kv: -kv[1]):
            weight = round(score / total, 4)
            matched_claim_ids = []
            for c in claims:
                text = (c.text if hasattr(c, "text") else c.get("text", "")).lower()
                claim_id = c.claim_id if hasattr(c, "claim_id") else c.get("claim_id")
                kws = self.categories[category]["keywords"]
                if any(kw in text for kw in kws):
                    matched_claim_ids.append(claim_id)
            results.append((category, weight, matched_claim_ids))
        return results
