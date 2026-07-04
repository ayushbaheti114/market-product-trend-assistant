"""
main.py
---------
CLI entry point / prototype demo for the AI-Powered Market Product Trend
Assistant.

Run modes:
    python main.py demo        -> loads sample_data, runs full pipeline,
                                   prints a market trend summary
    python main.py query "..."  -> runs a single conversational query
                                   against whatever is currently in the DB
    python main.py shell        -> interactive query loop (mini dashboard
                                   in the terminal)
    python main.py reset       -> wipes and reinitializes the database

This satisfies Success Criteria #4 (validated weighting logic via prototype
testing) by giving a runnable, inspectable end-to-end pipeline over sample
data before any real scraping/OCR integration is wired in.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
import storage.database as db
from ingestion.report_ingestor import load_json_report
from agents.orchestrator import OrchestratorAgent
from audit.audit_log import get_full_audit_trail


def setup():
    db.init_db()
    db.sync_categories()


def run_demo():
    setup()
    orchestrator = OrchestratorAgent()

    report_path = os.path.join(config.SAMPLE_DATA_DIR, "sample_products.json")
    loaded = load_json_report(report_path)

    print(f"\nLoaded {len(loaded)} products from sample report.\n")
    print("=" * 70)

    for product, row in loaded:
        result = orchestrator.process_product(
            product,
            image_path=None,
            fallback_ocr_text=row.get("ocr_text", ""),
        )
        print(f"\n>> {product.brand} - {product.name}  (${product.annual_revenue:,.0f}/yr)")
        print(f"   Claims extracted: {len(result['claims'])}")
        for c in result["claims"]:
            print(f"     - \"{c.text}\"  [confidence={c.confidence}]")
        print(f"   Hero ingredient(s): "
              f"{[i.canonical_name for i in result['ingredients'] if i.is_hero]}")
        print("   Category allocation:")
        for cat, weight, _ in result["category_weights"]:
            alloc_rev = round(product.annual_revenue * weight, 2)
            print(f"     - {cat}: {weight*100:.1f}%  (${alloc_rev:,.0f})")

    print("\n" + "=" * 70)
    print("MARKET TREND SUMMARY (aggregated across all products)")
    print("=" * 70)
    summary = db.category_revenue_summary()
    for row in summary:
        print(f"  {row['category']:<25} | products: {row['product_count']:<3} | "
              f"total revenue: ${row['total_revenue']:,.0f}")

    print(f"\nAudit log entries recorded: {len(get_full_audit_trail())}")
    print(f"\nDatabase written to: {config.DB_PATH}")
    print("Run 'streamlit run dashboard/app.py' to explore interactively.\n")

def run_query(prompt: str):
    setup()
    orchestrator = OrchestratorAgent()
    result = orchestrator.handle_query(prompt)
    print(f"\nIntent detected: {result['intent']}")
    print(f"Explanation: {result['explanation']}\n")
    print(json.dumps(result["data"], indent=2, default=str))

def run_shell():
    setup()
    orchestrator = OrchestratorAgent()
    print("Market Trend Assistant -- interactive query shell. Type 'exit' to quit.")
    print("Try: 'top categories', 'sleep', 'ingredients', 'product NB-SLEEP-001'\n")
    while True:
        try:
            prompt = input("query> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if prompt.lower() in ("exit", "quit"):
            break
        if not prompt:
            continue
        result = orchestrator.handle_query(prompt)
        print(f"\n[{result['intent']}] {result['explanation']}")
        print(json.dumps(result["data"], indent=2, default=str))
        print()

def run_reset():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    setup()
    print("Database reset and reinitialized.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [demo|query \"<text>\"|shell|reset]")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "demo":
        run_demo()
    elif mode == "query":
        if len(sys.argv) < 3:
            print("Usage: python main.py query \"<your question>\"")
            sys.exit(1)
        run_query(sys.argv[2])
    elif mode == "shell":
        run_shell()
    elif mode == "reset":
        run_reset()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
