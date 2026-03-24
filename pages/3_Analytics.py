import pandas as pd
import streamlit as st

from components.analytics_store import AnalyticsStore
from components.navigation import render_top_nav
from components.rag_config import load_rag_runtime_config
from components.theme import apply_theme_styles, init_theme_state

st.set_page_config(page_title="Analytics", page_icon=":material/insights:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_top_nav(active_page="analytics")

config = load_rag_runtime_config()
store = AnalyticsStore(config.analytics_db_path, enabled=config.enable_analytics)
if config.enable_analytics:
    store.apply_retention(
        max_days=config.analytics_retention_days,
        max_rows=config.analytics_retention_rows,
    )

st.title("Analytics")
st.caption("Operational metrics for retrieval, reranking, generation, and post-processing.")

if not config.enable_analytics:
    st.warning("Analytics are disabled. Set ENABLE_ANALYTICS=true to collect and view metrics.")
    st.stop()

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    days = st.slider("Lookback window (days)", min_value=1, max_value=180, value=30)

all_runs = store.read_query_runs(days=days)
model_options = ["All"] + sorted(all_runs["generation_model"].dropna().unique().tolist()) if not all_runs.empty else ["All"]
mode_options = ["All"] + sorted(all_runs["postprocess_mode"].dropna().unique().tolist()) if not all_runs.empty else ["All"]

with filter_col2:
    model_filter = st.selectbox("Generation model", model_options)
with filter_col3:
    rerank_filter = st.selectbox("Reranking", ["All", "Enabled", "Disabled"])
with filter_col4:
    postprocess_filter = st.selectbox("Post-process mode", mode_options)

rerank_enabled = None
if rerank_filter == "Enabled":
    rerank_enabled = True
elif rerank_filter == "Disabled":
    rerank_enabled = False

filtered_runs = store.read_query_runs(
    days=days,
    generation_model=None if model_filter == "All" else model_filter,
    rerank_enabled=rerank_enabled,
    postprocess_mode=None if postprocess_filter == "All" else postprocess_filter,
)

if filtered_runs.empty:
    st.info("No analytics data for the selected filters yet. Run a few queries in Ask the Assistant.")
    st.stop()

filtered_runs["success"] = pd.to_numeric(filtered_runs["success"], errors="coerce").fillna(0)
for metric_col in ["total_ms", "retrieval_ms", "rerank_ms", "generation_ms", "postprocess_ms"]:
    filtered_runs[metric_col] = pd.to_numeric(filtered_runs[metric_col], errors="coerce")

feedback_rows = store.read_feedback_rows(filtered_runs["run_id"].tolist())
source_click_rows = store.read_source_click_rows(filtered_runs["run_id"].tolist())

overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)
total_queries = int(len(filtered_runs))
success_rate = float(filtered_runs["success"].mean() * 100.0)
p50_total = float(filtered_runs["total_ms"].dropna().quantile(0.5)) if filtered_runs["total_ms"].notna().any() else 0.0
p95_total = float(filtered_runs["total_ms"].dropna().quantile(0.95)) if filtered_runs["total_ms"].notna().any() else 0.0

overview_col1.metric("Queries", str(total_queries))
overview_col2.metric("Success Rate", f"{success_rate:.1f}%")
overview_col3.metric("P50 Latency", f"{p50_total:.0f} ms")
overview_col4.metric("P95 Latency", f"{p95_total:.0f} ms")

quality_col1, quality_col2, quality_col3, quality_col4 = st.columns(4)
if feedback_rows.empty:
    helpful_count = 0
    needs_work_count = 0
    missing_evidence_count = 0
else:
    helpful_count = int((feedback_rows["feedback_type"] == "helpful").sum())
    needs_work_count = int((feedback_rows["feedback_type"] == "not_helpful").sum())
    missing_evidence_count = int((feedback_rows["feedback_type"] == "missing_evidence").sum())

quality_col1.metric("Helpful Votes", str(helpful_count))
quality_col2.metric("Needs Work Votes", str(needs_work_count))
quality_col3.metric("Missing Evidence Flags", str(missing_evidence_count))
quality_col4.metric("Source Opens", str(len(source_click_rows)))

trend_col1, trend_col2 = st.columns([1.4, 1.0], gap="large")
with trend_col1:
    st.subheader("Query Volume")
    trend_df = filtered_runs.copy()
    trend_df["ts"] = pd.to_datetime(trend_df["ts"], errors="coerce")
    trend_df = trend_df.dropna(subset=["ts"])
    trend_df["date"] = trend_df["ts"].dt.date
    daily = trend_df.groupby("date", as_index=False).agg(queries=("run_id", "count"))
    if not daily.empty:
        st.line_chart(daily.set_index("date"))
    else:
        st.info("No daily trend data available.")

with trend_col2:
    st.subheader("Latency by Stage")
    stage_summary = pd.DataFrame(
        {
            "Stage": ["Retrieval", "Reranking", "Generation", "Post-process"],
            "P50 ms": [
                filtered_runs["retrieval_ms"].median(skipna=True),
                filtered_runs["rerank_ms"].median(skipna=True),
                filtered_runs["generation_ms"].median(skipna=True),
                filtered_runs["postprocess_ms"].median(skipna=True),
            ],
            "P95 ms": [
                filtered_runs["retrieval_ms"].quantile(0.95),
                filtered_runs["rerank_ms"].quantile(0.95),
                filtered_runs["generation_ms"].quantile(0.95),
                filtered_runs["postprocess_ms"].quantile(0.95),
            ],
        }
    )
    stage_summary = stage_summary.fillna(0.0)
    st.dataframe(stage_summary, use_container_width=True, hide_index=True)

st.subheader("Model Comparison")
model_table = (
    filtered_runs.groupby("generation_model", as_index=False)
    .agg(
        queries=("run_id", "count"),
        success_rate=("success", "mean"),
        avg_total_ms=("total_ms", "mean"),
        p95_total_ms=("total_ms", lambda x: x.quantile(0.95)),
    )
    .sort_values("queries", ascending=False)
)
model_table["success_rate"] = (model_table["success_rate"] * 100.0).round(2)
model_table["avg_total_ms"] = model_table["avg_total_ms"].round(1)
model_table["p95_total_ms"] = model_table["p95_total_ms"].round(1)
st.dataframe(model_table, use_container_width=True, hide_index=True)

impact_col1, impact_col2 = st.columns(2, gap="large")
doc_rows = store.read_doc_rows(filtered_runs["run_id"].tolist())
with impact_col1:
    st.subheader("Reranking Effect")
    if doc_rows.empty:
        st.info("No reranking document-level metrics available yet.")
    else:
        selected = doc_rows[doc_rows["selected"] == 1].copy()
        selected["reordered"] = selected["rank_before"] != selected["rank_after"]
        reorder_rate = (
            selected.groupby("run_id")["reordered"].max().astype(float).mean() * 100.0
            if not selected.empty
            else 0.0
        )
        selected["score_lift"] = pd.to_numeric(selected["score_rerank"], errors="coerce") - pd.to_numeric(
            selected["score_raw"], errors="coerce"
        )
        score_lift = selected["score_lift"].dropna().mean()
        st.metric("Reordered Runs", f"{reorder_rate:.1f}%")
        if pd.notna(score_lift):
            st.metric("Avg Rerank Score Lift", f"{float(score_lift):.4f}")
        else:
            st.metric("Avg Rerank Score Lift", "N/A")

with impact_col2:
    st.subheader("Post-process Effect")
    refinement_rate = (
        pd.to_numeric(filtered_runs["refinement_applied"], errors="coerce").fillna(0).mean() * 100.0
        if "refinement_applied" in filtered_runs.columns
        else 0.0
    )
    avg_chars = pd.to_numeric(filtered_runs["response_chars"], errors="coerce").mean()
    st.metric("LLM Refinement Usage", f"{refinement_rate:.1f}%")
    st.metric("Avg Response Length", f"{0 if pd.isna(avg_chars) else int(avg_chars)} chars")

feedback_col1, feedback_col2 = st.columns(2, gap="large")
with feedback_col1:
    st.subheader("Answer Feedback")
    if feedback_rows.empty:
        st.info("No answer feedback has been submitted yet.")
    else:
        feedback_summary = (
            feedback_rows.groupby("feedback_type", as_index=False)
            .agg(events=("feedback_type", "count"))
            .sort_values("events", ascending=False)
        )
        st.dataframe(feedback_summary, use_container_width=True, hide_index=True)

with feedback_col2:
    st.subheader("Top Opened Sources")
    if source_click_rows.empty:
        st.info("No source opens have been recorded yet.")
    else:
        source_summary = (
            source_click_rows.groupby(["title", "source"], as_index=False)
            .agg(opens=("run_id", "count"))
            .sort_values("opens", ascending=False)
            .head(10)
        )
        st.dataframe(source_summary, use_container_width=True, hide_index=True)

st.subheader("Recent Runs")
recent_cols = [
    "ts",
    "generation_model",
    "postprocess_mode",
    "rerank_enabled",
    "success",
    "total_ms",
    "retrieved_docs",
    "selected_docs",
    "warning_text",
]
existing_cols = [col for col in recent_cols if col in filtered_runs.columns]
display_runs = filtered_runs[existing_cols].head(50).copy()
st.dataframe(display_runs, use_container_width=True, hide_index=True)
