# AI-Powered Market Product Trend Assistant — Prototype

A working Python prototype of the multi-agent market intelligence platform
described in the project brief for the health & wellness supplements
industry. It replicates the manual "packaging → claims → category →
revenue" analysis workflow, automates it end-to-end, and exposes it through
a queryable dashboard with full traceability and human-in-the-loop
governance.

## Architecture

```
market_trend_assistant/
├── config.py                  # Manually-curated benefit categories, ingredient
│                               # dictionary, claim trigger phrases
├── models.py                  # Product, Claim, Ingredient, RevenueAllocation,
│                               # AuditEntry dataclasses
├── storage/
│   └── database.py            # SQLite persistence + audit logging + aggregation queries
├── ingestion/
│   ├── report_ingestor.py     # Loads structured CSV/JSON market reports
│   └── image_scraper.py       # Retailer/brand image discovery (robots.txt aware)
├── agents/
│   ├── base.py                     # Shared agent base (optional Claude API hook)
│   ├── claims_agent.py             # Product Claims Agent (OCR + claim extraction)
│   ├── ingredient_agent.py         # Hero Ingredient Extractor Agent
│   ├── market_matching_agent.py    # Market Matching Agent (SKU → benefit category)
│   ├── revenue_agent.py            # Revenue Attribution Agent
│   └── orchestrator.py             # Orchestrator Agent (pipeline + query routing)
├── audit/
│   └── audit_log.py           # Human override helpers with governance tracking
├── dashboard/
│   └── app.py                 # Streamlit dashboard (conversational + drill-down + overrides)
├── sample_data/
│   └── sample_products.json   # 8 sample supplement products for demo/testing
└── main.py                    # CLI: demo / query / shell / reset
```

## How it maps to the brief

| Brief requirement | Implementation |
|---|---|
| Ingest structured market data | `ingestion/report_ingestor.py` (CSV/JSON) |
| Scrape retailer/brand images | `ingestion/image_scraper.py` (robots.txt-checked skeleton) |
| Extract claims via OCR/CV | `agents/claims_agent.py` (pytesseract + rule-based/LLM claim detection) |
| Identify hero ingredients | `agents/ingredient_agent.py` |
| Allocate revenue by weighted claims | `agents/revenue_agent.py` |
| Map SKUs to benefit categories | `agents/market_matching_agent.py` (scores against `config.BENEFIT_CATEGORIES`) |
| Orchestrate agents from a prompt | `agents/orchestrator.py` |
| Interactive dashboard + conversational querying | `dashboard/app.py` |
| Traceability insight → source | `storage.database.product_trace()`, Audit Trail tab |
| Human-in-the-loop + audit tracking | `audit/audit_log.py`, `storage.database.apply_human_override()` |
| Categories stay manually controlled | `config.BENEFIT_CATEGORIES`, synced via `sync_categories()` (never AI-generated) |
| Prioritize packaging images over web copy | Claims Agent takes image/OCR text as primary input; scraper only fetches images, not copy |

## Setup

```bash
pip install -r requirements.txt
```

Core functionality (pipeline + CLI + dashboard tables) runs with only
`pandas` and `streamlit` installed — OCR, live scraping, and LLM extraction
are optional and degrade gracefully to rule-based fallbacks if their
libraries or credentials aren't present. This lets the prototype satisfy
**Success Criteria #4** (validate weighting logic via prototype testing)
without needing real infrastructure on day one.

To enable LLM-assisted claim extraction:

```bash
export ANTHROPIC_API_KEY="sk-..."
```

## Running the prototype

**1. Run the full pipeline against sample data (CLI):**

```bash
python main.py demo
```

This loads 8 sample supplement products, runs each through Claims →
Ingredients → Market Matching → Revenue Attribution, and prints a market
trend summary aggregated by benefit category.

**2. Ask a one-off question:**

```bash
python main.py query "top categories"
python main.py query "product NB-SLEEP-001"
python main.py query "ingredients"
```

**3. Interactive terminal shell:**

```bash
python main.py shell
```

**4. Full dashboard (recommended):**

```bash
streamlit run dashboard/app.py
```

Click **"Load & Process Sample Data"** in the sidebar, then explore:
- Conversational query box
- Category revenue bar chart / drill-down table
- Per-product traceability (claims → source snippet → ingredients → revenue)
- Human override forms for claim category / revenue weight, each writing to
  the audit trail
- Full audit log view

**5. Reset the database:**

```bash
python main.py reset
```

## Extending toward production

- **Real OCR**: install `pytesseract` + a Tesseract binary, or swap in a
  hosted vision API inside `agents/claims_agent.py::ocr_image`.
- **Real scraping**: `ingestion/image_scraper.py` includes a robots.txt
  check and rate limiting; each target retailer/brand still needs a
  case-by-case legal/compliance review per the brief's constraints.
- **LLM-assisted extraction**: set `ANTHROPIC_API_KEY`; `config.USE_LLM`
  auto-enables Claude-based claim extraction with rule-based fallback.
- **Governance rules**: `audit/audit_log.py` is the seam where approval
  workflows (e.g., requiring a second reviewer for overrides above a
  revenue threshold) would be added.
- **"Analysis completeness" definition**: currently a placeholder gap per
  the brief's Constraints section — a natural next addition is a
  completeness score per product (e.g., % of expected fields populated:
  image present, ≥1 claim extracted, ≥1 category matched, revenue
  allocated) surfaced in the dashboard.
- **Swap SQLite for Postgres**: `storage/database.py` isolates all SQL, so
  this is a contained change if/when concurrent multi-user access is needed.
