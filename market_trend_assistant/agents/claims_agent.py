"""
agents/claims_agent.py
Product Claims Agent.
Priority per Strategic Decision #2: packaging IMAGES are the primary claim
source (via OCR + computer vision), with website copy as a secondary /
future-scope input. This agent:

  1. Runs OCR on a packaging image (pytesseract if available; falls back to
     pre-supplied ocr_text for environments without an OCR binary installed).
  2. Scans the resulting text for claim trigger phrases.
  3. Emits Claim objects with the exact source snippet retained for
     traceability (Key Capability #4).
"""

import os
import re
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.base import BaseAgent
from models import Claim, new_id

class ProductClaimsAgent(BaseAgent):
    name = "ProductClaimsAgent"

    def ocr_image(self, image_path: str, fallback_text: str = "") -> str:
        """Attempt OCR via pytesseract; otherwise use fallback_text (useful
        for the prototype/demo where a real OCR binary may not be present)."""
        if image_path and os.path.exists(image_path):
            try:
                import pytesseract
                from PIL import Image
                return pytesseract.image_to_string(Image.open(image_path))
            except Exception as e:
                self.log(f"OCR unavailable ({e}); using fallback text.")
        return fallback_text

    def extract_claims_rule_based(self, product_id: str, text: str,
                                   source_image_id: str = None):
        """Sentence-split the OCR text and flag sentences containing a
        known claim trigger phrase."""
        claims = []
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            lowered = s.lower()
            hit_phrases = [p for p in config.CLAIM_TRIGGER_PHRASES if p in lowered]
            if hit_phrases:
                confidence = min(0.5 + 0.15 * len(hit_phrases), 0.95)
                claims.append(Claim(
                    claim_id=new_id("claim"),
                    product_id=product_id,
                    text=s,
                    confidence=round(confidence, 2),
                    source_image_id=source_image_id,
                    source_snippet=s,
                    extraction_method="rule_based",
                ))
        return claims

    def extract_claims_llm(self, product_id: str, text: str,
                            source_image_id: str = None):
        """LLM-assisted extraction for higher recall/precision. Only used
        when config.USE_LLM is True."""
        system_prompt = (
            "You extract marketing/benefit claims from supplement packaging "
            "OCR text. Return one claim per line, verbatim substrings of the "
            "input only. No commentary, no numbering."
        )
        raw = self.call_llm(system_prompt, text)
        claims = []
        for line in raw.splitlines():
            line = line.strip("-• ").strip()
            if line:
                claims.append(Claim(
                    claim_id=new_id("claim"),
                    product_id=product_id,
                    text=line,
                    confidence=0.75,
                    source_image_id=source_image_id,
                    source_snippet=line,
                    extraction_method="llm",
                ))
        return claims

    def run(self, product_id: str, image_path: str = None,
            fallback_text: str = "", source_image_id: str = None):
        text = self.ocr_image(image_path, fallback_text)
        if config.USE_LLM:
            try:
                claims = self.extract_claims_llm(product_id, text, source_image_id)
                if claims:
                    return claims
            except Exception as e:
                self.log(f"LLM extraction failed ({e}); falling back to rules.")
        return self.extract_claims_rule_based(product_id, text, source_image_id)
