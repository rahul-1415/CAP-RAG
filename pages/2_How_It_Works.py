import streamlit as st

from components.navigation import render_top_nav
from components.rag_config import load_rag_runtime_config
from components.theme import apply_theme_styles, init_theme_state

st.set_page_config(page_title="How It Works", page_icon=":material/schema:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_top_nav(active_page="how_it_works")
config = load_rag_runtime_config()

st.title("How It Works")
st.caption("From user query to policy-grounded answer.")

st.subheader("System Flow")
st.markdown(
    """
1. **User asks a question** in the chat interface.
2. **Conversation-aware query rewriting** expands short follow-ups with recent user turns when needed.
3. **Hybrid retrieval searches candidate chunks** using dense similarity plus lexical BM25-style scoring.
4. **Cohere reranker optionally reorders candidates** for relevance and keeps top chunks (`k` from UI).
5. **Post-processing rules clean context** (normalization, deduplication, chunk balancing).
6. **LLM generates a cited response** using only post-processed context and inline `[DOC_n]` references.
7. **Optional post-LLM refinement** rewrites for clarity without adding facts or removing citations.
8. **Evidence + run metrics are shown per answer** and analytics are persisted for monitoring.
"""
)

st.subheader("Technical Components")
st.markdown(
    f"""
- **Embedding model**: `BAAI/bge-small-en-v1.5`
- **Vector DB**: Chroma (persistent local directory)
- **Retriever mode**: MMR candidate retrieval (diversified results)
- **Hybrid retrieval**: Dense ranking fused with lexical scoring over the indexed corpus
- **Reranker**: Cohere Rerank (`rerank-v3.5` default, optional/fallback-safe)
- **Retrieval depth control**: `Documents to check` in the UI (`1-20`, default `5`)
- **Post-processing modes**: `none`, `rules_only`, `rules_plus_llm`
- **Generation models**: `{", ".join(config.model_options)}`
- **Analytics**: SQLite run logs + Streamlit Analytics dashboard + answer feedback/source-open events
- **UI**: Streamlit chat interface with multi-session history
"""
)

st.subheader("Retrieval Depth Guidance")
st.markdown(
    """
- Use **3-5 documents** for faster answers on focused questions.
- Use **6-10 documents** for comparison questions across policies or cities.
- Use **10+ documents** when you want broader context, with slightly longer response time.
- Keep **Reranking ON** when using larger document pools for better precision.
"""
)

st.subheader("Post-Processing Guidance")
st.markdown(
    """
- **none**: fastest path, useful for quick experimentation.
- **rules_only**: recommended default for stable quality/latency balance.
- **rules_plus_llm**: best readability, but higher latency and token usage.
- All answer modes now aim to preserve inline `[DOC_n]` citations back to the retrieved evidence.
"""
)

st.subheader("Use-Case Examples")
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "City Climate Office",
        "Transport Planning",
        "Grant / Funding Prep",
        "Academic Research",
    ]
)

with tab1:
    st.markdown(
        """
**Goal**: Identify actions to reduce building emissions in cities.  
**Example prompt**: "What building retrofit policies are most commonly recommended in C40 case studies?"  
**Suggested documents to check**: `8`  
**What the app returns**: A summarized set of retrofit approaches grounded in retrieved policy documents, with citations and expandable evidence.
"""
    )

with tab2:
    st.markdown(
        """
**Goal**: Plan mobility decarbonization options.  
**Example prompt**: "What policies support electric bus adoption and low-emission zones?"  
**Suggested documents to check**: `6`  
**What the app returns**: Policy levers, implementation notes, and evidence excerpts from relevant documents.
"""
    )

with tab3:
    st.markdown(
        """
**Goal**: Draft evidence-backed proposals for climate funding.  
**Example prompt**: "Give policy examples for urban heat adaptation that can justify funding requests."  
**Suggested documents to check**: `10`  
**What the app returns**: Context-grounded bullet points and references usable in grant narratives.
"""
    )

with tab4:
    st.markdown(
        """
**Goal**: Compare policy patterns across themes.  
**Example prompt**: "Compare adaptation vs mitigation policy recommendations in the dataset."  
**Suggested documents to check**: `12`  
**What the app returns**: A structured comparison based on retrieved passages, not generic model knowledge, plus source panels for each answer.
"""
    )

st.subheader("Prompt Patterns That Work Well")
st.code(
    """- "Summarize policy recommendations for [topic] in [region/city context]."
- "Compare approaches for [policy A] vs [policy B] using source evidence."
- "List implementation steps, barriers, and enablers for [climate action]."
- "What data points from C40 examples can support a proposal on [theme]?" """
)
