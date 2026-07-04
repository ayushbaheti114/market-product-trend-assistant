"""
agents/ingredient_agent.py
Hero Ingredient Extractor Agent.
Identifies key active ingredients mentioned in claim text / OCR text and
normalizes them against config.INGREDIENT_ALIASES. The ingredient mentioned
earliest / most frequently is flagged as the "hero" ingredient (the one the
brand is positioning the product around), consistent with the manual
process this system replicates.
"""
import os
import re
import sys
from collections import Counter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.base import BaseAgent
from models import Ingredient, new_id

class HeroIngredientExtractorAgent(BaseAgent):
    name = "HeroIngredientExtractorAgent"
    def _find_mentions(self, text: str):
        """Uses word-boundary regex matching rather than naive substring
        search, since short aliases like "dha" (Omega-3) would otherwise
        false-positive inside unrelated words like "ashwagandha"."""
        lowered = text.lower()
        mentions = []  # (canonical_name, raw_mention, first_index)
        for canonical, aliases in config.INGREDIENT_ALIASES.items():
            for alias in aliases:
                pattern = r"\b" + re.escape(alias) + r"\b"
                match = re.search(pattern, lowered)
                if match:
                    mentions.append((canonical, alias, match.start()))
                    break
        return mentions

    def run(self, product_id: str, claims, full_ocr_text: str = ""):
        """claims: list of Claim objects (or dicts with 'text'/'claim_id').
        full_ocr_text: complete packaging OCR text, since ingredient names
        (e.g. "Melatonin 5mg") often appear in the ingredient panel rather
        than in a benefit-claim sentence and would otherwise be missed."""
        claims_text = " ".join(
            (c.text if hasattr(c, "text") else c.get("text", "")) for c in claims
        )
        full_text = f"{full_ocr_text} {claims_text}".strip()
        mentions = self._find_mentions(full_text)
        if not mentions:
            return []

        mentions.sort(key=lambda m: m[2])  # earliest mention first
        counts = Counter(m[0] for m in mentions)
        hero_name = mentions[0][0]  # earliest-mentioned = hero, matches
                                     # typical front-of-pack ingredient billing

        results = []
        seen = set()
        for canonical, raw_mention, _ in mentions:
            if canonical in seen:
                continue
            seen.add(canonical)
            # attribute to the claim that contains the mention, if findable
            source_claim_id = None
            pattern = r"\b" + re.escape(raw_mention) + r"\b"
            for c in claims:
                text = c.text if hasattr(c, "text") else c.get("text", "")
                if re.search(pattern, text.lower()):
                    source_claim_id = c.claim_id if hasattr(c, "claim_id") else c.get("claim_id")
                    break
            results.append(Ingredient(
                ingredient_id=new_id("ing"),
                product_id=product_id,
                canonical_name=canonical,
                raw_mention=raw_mention,
                is_hero=(canonical == hero_name),
                source_claim_id=source_claim_id,
            ))
        return results
