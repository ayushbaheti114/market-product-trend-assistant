"""
config.py
Central configuration for the AI-Powered Market Product Trend Assistant.
Per the project's strategic decisions:
  - Top-level benefit categories remain under MANUAL control (Strategic Decision #1).
    They are defined here as an editable dictionary rather than being inferred by AI.
  - Packaging image analysis is prioritized over website copy (Strategic Decision #2).
To update the category taxonomy, edit BENEFIT_CATEGORIES below and re-run the
Market Matching Agent. Every change is automatically timestamped in the audit log
when loaded through storage.database.sync_categories().
"""

import os
# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "market_intel.db")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")
IMAGE_CACHE_DIR = os.path.join(BASE_DIR, "image_cache")

os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Benefit categories (MANUALLY CURATED — see Strategic Decision #1)
# Each category maps to a set of keyword signals used by the Market Matching
# Agent. Weight = relative importance of a keyword hit within that category.
BENEFIT_CATEGORIES = {
    "Sleep & Relaxation": {
        "keywords": {
            "sleep": 1.0, "melatonin": 1.0, "calm": 0.7, "relax": 0.7,
            "restful": 0.8, "insomnia": 0.9, "unwind": 0.6, "nighttime": 0.6,
        }
    },
    "Energy & Performance": {
        "keywords": {
            "energy": 1.0, "performance": 0.8, "caffeine": 0.7, "endurance": 0.8,
            "stamina": 0.8, "focus": 0.6, "pre-workout": 0.9, "vitality": 0.7,
        }
    },
    "Immune Support": {
        "keywords": {
            "immune": 1.0, "immunity": 1.0, "vitamin c": 0.7, "zinc": 0.6,
            "elderberry": 0.8, "defense": 0.6, "wellness": 0.4,
        }
    },
    "Digestive Health": {
        "keywords": {
            "digestive": 1.0, "gut": 0.9, "probiotic": 1.0, "prebiotic": 0.9,
            "fiber": 0.6, "bloating": 0.7, "gi health": 0.8,
        }
    },
    "Stress & Mood": {
        "keywords": {
            "stress": 1.0, "mood": 0.9, "anxiety": 0.8, "adaptogen": 0.8,
            "ashwagandha": 0.9, "cortisol": 0.7, "mental wellness": 0.7,
        }
    },
    "Joint & Mobility": {
        "keywords": {
            "joint": 1.0, "mobility": 0.9, "flexibility": 0.7, "cartilage": 0.7,
            "glucosamine": 0.9, "collagen": 0.6, "arthritis": 0.7,
        }
    },
    "Beauty & Skin": {
        "keywords": {
            "skin": 1.0, "hair": 0.8, "nails": 0.6, "biotin": 0.8,
            "collagen": 0.9, "radiance": 0.6, "anti-aging": 0.8,
        }
    },
    "Weight Management": {
        "keywords": {
            "weight": 1.0, "metabolism": 0.8, "fat burn": 0.9, "appetite": 0.7,
            "lean": 0.6, "thermogenic": 0.8,
        }
    },
    "Cognitive Health": {
        "keywords": {
            "brain": 1.0, "cognitive": 1.0, "memory": 0.9, "clarity": 0.6,
            "nootropic": 0.9, "focus": 0.7,
        }
    },
    "Heart Health": {
        "keywords": {
            "heart": 1.0, "cardiovascular": 1.0, "cholesterol": 0.8,
            "omega-3": 0.8, "blood pressure": 0.7, "circulation": 0.6,
        }
    },
}
# Hero ingredient reference dictionary (canonical name -> aliases)
# Used by the Hero Ingredient Extractor Agent for normalization.
INGREDIENT_ALIASES = {
    "Ashwagandha": ["ashwagandha", "withania somnifera"],
    "Melatonin": ["melatonin"],
    "Vitamin C": ["vitamin c", "ascorbic acid"],
    "Zinc": ["zinc", "zinc gluconate", "zinc citrate"],
    "Probiotics": ["probiotic", "probiotics", "lactobacillus", "bifidobacterium"],
    "Collagen": ["collagen", "collagen peptides", "hydrolyzed collagen"],
    "Glucosamine": ["glucosamine", "glucosamine sulfate"],
    "Caffeine": ["caffeine", "caffeine anhydrous", "guarana"],
    "Omega-3": ["omega-3", "omega 3", "fish oil", "epa", "dha"],
    "Biotin": ["biotin", "vitamin b7"],
    "Elderberry": ["elderberry", "sambucus"],
    "Magnesium": ["magnesium", "magnesium glycinate", "magnesium citrate"],
    "L-Theanine": ["l-theanine", "theanine"],
    "Turmeric": ["turmeric", "curcumin"],
    "Fiber": ["fiber", "inulin", "psyllium"],
}
# Claim trigger phrases — used by the Product Claims Agent to flag
# marketing/benefit claims within OCR'd packaging text.
CLAIM_TRIGGER_PHRASES = [
    "supports", "helps", "promotes", "boosts", "improves", "enhances",
    "clinically proven", "clinically studied", "reduces", "relieves",
    "maintains", "restores", "protects", "strengthens", "aids in",
]
# LLM integration (optional). If ANTHROPIC_API_KEY is set in the environment,
# agents will use Claude for higher-quality extraction. Otherwise agents fall
# back to deterministic rule-based / dictionary matching so the pipeline is
# fully runnable offline for the prototype (Success Criteria #4).
USE_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))
LLM_MODEL = "claude-sonnet-4-6"
