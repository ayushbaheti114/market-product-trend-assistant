"""
dashboard/app.py
Interactive dashboard (Key Capability #1-5 from the brief):
  1. Conversational querying (chat box -> OrchestratorAgent.handle_query)
  2. Drill-down analysis across categories and sub-segments
  3. Dynamic refresh (re-run pipeline button)
  4. Traceability from insight to source data (product detail view)
  5. Human-in-the-loop overrides with audit tracking
Run with:  streamlit run dashboard/app.py
"""
import os
import sys
import pandas as pd
import streamlit as st
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import storage.database as db
from agents.orchestrator import OrchestratorAgent
from ingestion.report_ingestor import load_json_report
from audit.audit_log import (
    override_claim_category, override_revenue_weight,
    override_hero_ingredient, get_full_audit_trail,
)

st.set_page_config(page_title="Market Product Trend Assistant", layout="wide")
db.init_db()
db.sync_categories()
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = OrchestratorAgent()
orchestrator = st.session_state.orchestrator
st.title("🧪AI-Powered Market Product Trend Assistant")
st.caption("Prototype dashboard — health & wellness supplement market intelligence")

# Sidebar: data refresh / ingestion controls
with st.sidebar:
    st.header("Data Controls")
    st.write("Load / refresh the sample market report and reprocess through "
             "all agents.")
    if st.button("🔄 Load & Process Sample Data"):
        report_path = os.path.join(config.SAMPLE_DATA_DIR, "sample_products.json")
        loaded = load_json_report(report_path)
        progress = st.progress(0)
        for i, (product, row) in enumerate(loaded):
            orchestrator.process_product(
                product, fallback_ocr_text=row.get("ocr_text", "")
            )
            progress.progress((i + 1) / len(loaded))
        st.success(f"Processed {len(loaded)} products.")

    if st.button("🗑️ Reset Database"):
        import time
        if os.path.exists(config.DB_PATH):
            os.remove(config.DB_PATH)
        db.init_db()
        db.sync_categories()
        st.success("Database reset.")
        time.sleep(0.5)
        st.rerun()

    st.divider()
    st.caption(
        "Categories are manually curated in config.py (Strategic Decision #1). "
        f"Currently loaded: {len(config.BENEFIT_CATEGORIES)} categories."
    )

# Conversational query box
st.subheader("💬 Ask the Assistant")
query = st.text_input(
    "Try: \"top categories\", \"sleep\", \"ingredients\", \"product NB-SLEEP-001\""
)
if query:
    result = orchestrator.handle_query(query)
    st.info(f"**Intent:** {result['intent']}  \n**Explanation:** {result['explanation']}")

    if result["intent"] == "top_categories" and result["data"]:
        df = pd.DataFrame(result["data"])
        st.bar_chart(df.set_index("category")["total_revenue"])
        st.dataframe(df, use_container_width=True)

    elif result["intent"] == "category_drilldown":
        st.dataframe(pd.DataFrame(result["data"]), use_container_width=True)

    elif result["intent"] == "ingredient_frequency":
        df = pd.DataFrame(result["data"], columns=["ingredient", "count"])
        st.bar_chart(df.set_index("ingredient")["count"])

    elif result["intent"] == "product_trace":
        trace = result["data"]
        st.json(trace)

    else:
        st.json(result["data"])

st.divider()

# Main drill-down: category revenue summary
st.subheader("📊 Market Trend Overview")
summary = db.category_revenue_summary()
if summary:
    df_summary = pd.DataFrame(summary)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.bar_chart(df_summary.set_index("category")["total_revenue"])
    with col2:
        st.metric("Total Categories", len(df_summary))
        st.metric("Total Allocated Revenue", f"${df_summary['total_revenue'].sum():,.0f}")
    st.dataframe(df_summary, use_container_width=True)
else:
    st.warning("No data yet — click 'Load & Process Sample Data' in the sidebar.")

st.divider()

# Product-level traceability + human-in-the-loop overrides
st.subheader("🔍 Product Traceability & Human Overrides")
products = db.fetch_all("products")
if products:
    labels = {f"{p['brand']} — {p['name']} ({p['sku']})": p["product_id"] for p in products}
    chosen_label = st.selectbox("Select a product", list(labels.keys()))
    product_id = labels[chosen_label]
    trace = db.product_trace(product_id)

    tab1, tab2, tab3, tab4 = st.tabs(["Claims", "Ingredients", "Revenue Allocation", "Audit Trail"])

    with tab1:
        claims_df = pd.DataFrame(trace["claims"])
        st.dataframe(claims_df, use_container_width=True)
        if not claims_df.empty:
            st.markdown("**Override a claim's category:**")
            claim_choice = st.selectbox("Claim", claims_df["claim_id"].tolist(), key="claim_override")
            new_cat = st.selectbox("New category", list(config.BENEFIT_CATEGORIES.keys()), key="new_cat")
            reason = st.text_input("Override reason", key="claim_reason")
            if st.button("Apply claim override") and reason:
                override_claim_category(claim_choice, new_cat, actor="dashboard_user", reason=reason)
                st.success("Override applied and logged to audit trail.")
                st.rerun()

    with tab2:
        st.dataframe(pd.DataFrame(trace["ingredients"]), use_container_width=True)

    with tab3:
        alloc_df = pd.DataFrame(trace["revenue_allocations"])
        st.dataframe(alloc_df, use_container_width=True)
        if not alloc_df.empty:
            st.markdown("**Override a revenue allocation weight:**")
            alloc_choice = st.selectbox("Allocation", alloc_df["allocation_id"].tolist(), key="alloc_override")
            new_weight = st.slider("New weight (0-1)", 0.0, 1.0, 0.5, key="new_weight")
            reason2 = st.text_input("Override reason", key="alloc_reason")
            if st.button("Apply revenue override") and reason2:
                override_revenue_weight(alloc_choice, new_weight, actor="dashboard_user", reason=reason2)
                st.success("Override applied and logged to audit trail.")
                st.rerun()

    with tab4:
        st.dataframe(pd.DataFrame(trace["audit_trail"]), use_container_width=True)
else:
    st.info("No products loaded yet.")

st.divider()
st.subheader("🧾 Full Audit Log")
audit_rows = get_full_audit_trail()
if audit_rows:
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)
else:
    st.caption("No audit entries yet.")
