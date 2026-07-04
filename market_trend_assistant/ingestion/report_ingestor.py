"""
ingestion/report_ingestor.py
Ingests structured market data from third-party reports (CSV/JSON), which
per the Constraints section may arrive as manual uploads rather than via
API. This module is deliberately format-tolerant.
Expected minimal columns/fields per product row:
    brand, name, sku, annual_revenue, retailer (optional),
    ocr_text (optional -- pre-transcribed packaging text for the demo),
    image_url (optional)
"""
import csv
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Product, new_id
import storage.database as db
def load_json_report(filepath: str):
    with open(filepath, "r") as f:
        rows = json.load(f)
    return _ingest_rows(rows)

def load_csv_report(filepath: str):
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return _ingest_rows(rows)

def _ingest_rows(rows):
    """Converts raw dict rows into Product objects, inserts into DB, and
    returns (Product, raw_row) tuples so the caller can access
    ocr_text/image_url for downstream agent processing."""
    results = []
    for row in rows:
        product = Product(
            product_id=new_id("prod"),
            brand=row.get("brand", "Unknown"),
            name=row.get("name", "Unnamed Product"),
            sku=row.get("sku", "N/A"),
            annual_revenue=float(row.get("annual_revenue", 0) or 0),
            retailer=row.get("retailer", ""),
            raw_source=row.get("raw_source", "manual_upload"),
        )
        db.insert_product(product)
        results.append((product, row))
    return results
