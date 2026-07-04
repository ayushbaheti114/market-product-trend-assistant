"""
agents/revenue_agent.py
Revenue Attribution Agent.
Allocates a product's total annual revenue proportionally across the
benefit categories it was matched to, using the weights produced by the
Market Matching Agent. This directly replicates the manual analyst step of
splitting SKU revenue across multiple benefit claims when a product
straddles categories (e.g., a "Sleep + Stress" gummy).
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import BaseAgent
from models import RevenueAllocation, new_id
class RevenueAttributionAgent(BaseAgent):
    name = "RevenueAttributionAgent"

    def run(self, product_id: str, annual_revenue: float, category_weights):
        """category_weights: list of (category, weight, matched_claim_ids)
        as produced by MarketMatchingAgent.run(). Weights should already sum
        to ~1.0; this agent re-normalizes defensively in case they don't."""
        total_weight = sum(w for _, w, _ in category_weights) or 1.0
        allocations = []
        for category, weight, _ in category_weights:
            normalized = weight / total_weight
            allocations.append(RevenueAllocation(
                allocation_id=new_id("alloc"),
                product_id=product_id,
                category=category,
                allocated_revenue=round(annual_revenue * normalized, 2),
                weight=round(normalized, 4),
                basis="claim_weighted",
            ))
        return allocations
