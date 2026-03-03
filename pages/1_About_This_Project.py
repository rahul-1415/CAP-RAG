import streamlit as st

from components.navigation import render_top_nav
from components.theme import apply_theme_styles, init_theme_state, render_dark_mode_slider

st.set_page_config(page_title="About This Project", page_icon=":material/info:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_dark_mode_slider()
render_top_nav(active_page="about")

st.title("About This Project")
st.caption("Climate Policy RAG System based on C40 Knowledge Hub climate-policy content.")

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Primary Source", "C40 Knowledge Hub")
metric_col2.metric("Articles Collected", "795")
metric_col3.metric("Core Approach", "RAG + Llama")

st.subheader("Project Purpose")
st.markdown(
    """
This project helps users ask climate policy questions and get grounded, context-aware answers.
The assistant retrieves relevant policy passages first, then generates an answer constrained to that context.
Users can control retrieval depth from the chat page using **Documents to check** (default: `5`).
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
3. A generation layer using Groq-hosted Llama models.
4. A Streamlit app for query input, evidence viewing, answer generation, and multi-chat history.
5. A retrieval depth selector (`Documents to check`) so users can tune breadth vs speed per query.
"""
)

st.subheader("Current Deployment Notes")
st.markdown(
    """
- Designed for lightweight web deployment with a persistent Chroma directory.
- Caching is used to reduce repeated retriever/model initialization costs.
- Higher document counts can improve coverage but may increase retrieval and generation time.
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
