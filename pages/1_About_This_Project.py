import streamlit as st

from components.navigation import render_top_nav
from components.rag_config import load_rag_runtime_config
from components.retriever import get_collection_stats
from components.theme import apply_theme_styles, init_theme_state

st.set_page_config(page_title="About This Project", page_icon=":material/info:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_top_nav(active_page="about")
config = load_rag_runtime_config()
collection_stats = get_collection_stats()

st.title("About This Project")
st.caption("Climate Policy RAG System based on C40 Knowledge Hub climate-policy content.")

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Primary Source", "C40 Knowledge Hub")
metric_col2.metric("Documents Indexed", str(collection_stats.document_count))
metric_col3.metric("Core Approach", "Hybrid RAG + Groq")

st.subheader("Project Purpose")
st.markdown(
    """
This project helps users ask climate policy questions and get grounded, context-aware answers.
The assistant retrieves relevant policy passages first, then generates an answer constrained to that context.
Follow-up questions can reuse recent chat context so shorter conversational prompts still retrieve the right material.
Users can control retrieval depth from the chat page using **Documents to check** (default: `5`).
The current version also supports **hybrid dense + lexical retrieval, external reranking, rule-based post-processing, optional LLM refinement, inline citations, per-answer evidence panels, and analytics logging**.
"""
)

st.subheader("Data and Scope")
st.markdown(
    """
- All policy content comes from **https://www.c40knowledgehub.org/**.
- The knowledge base was built from collected climate-policy articles.
- The app is intended for policy exploration, drafting support, and structured research.
"""
)

st.subheader("What Has Been Built")
st.markdown(
    """
1. Automated data collection and preparation pipeline for C40 policy articles.
2. A retrieval layer using Chroma vector storage and sentence embeddings.
3. A hybrid retrieval pass that blends dense similarity with keyword-aware lexical ranking.
4. A reranking layer using Cohere Rerank (with graceful fallback when unavailable).
5. A generation layer using Groq-hosted Llama models with inline `[DOC_n]` citations.
6. A deterministic post-processing layer plus optional LLM rewrite for clarity.
7. Persistent analytics logging in SQLite, answer feedback capture, and source-open tracking.
8. A Streamlit app for query input, evidence viewing per answer, and multi-chat history.
9. A retrieval depth selector (`Documents to check`) so users can tune breadth vs speed per query.
"""
)

st.subheader("Current Deployment Notes")
st.markdown(
    f"""
- Designed for lightweight web deployment with a persistent Chroma directory.
- Caching is used to reduce repeated retriever/model initialization costs.
- Higher document counts can improve coverage but may increase retrieval and generation time.
- If `COHERE_API_KEY` is missing, reranking automatically falls back to base retrieval order.
- Analytics data is stored locally at `analytics/rag_metrics.sqlite3` by default.
- Available generation models are loaded from runtime config: `{", ".join(config.model_options)}`.
- Restart spikes are usually caused by limited instance resources or cold starts.
"""
)

st.subheader("Who This Is For")
st.markdown(
    """
- City policy teams exploring practical climate actions.
- Students and researchers comparing policy measures.
- NGOs and analysts preparing evidence-backed recommendations.
"""
)
