import streamlit as st

from components.navigation import render_top_nav
from components.rag_config import load_rag_runtime_config
from components.retriever import get_collection_stats
from components.theme import apply_theme_styles, init_theme_state, render_dark_mode_slider

st.set_page_config(page_title="Settings", page_icon=":material/settings:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_top_nav(active_page="settings")
config = load_rag_runtime_config()
collection_stats = get_collection_stats()

st.title("Settings")
st.caption("Adjust global application preferences.")

with st.container(border=True):
    st.markdown('<div class="panel-title">Appearance</div>', unsafe_allow_html=True)
    render_dark_mode_slider()
    st.caption("Theme preference applies across all tabs and remains in the URL query param.")

with st.container(border=True):
    st.markdown('<div class="panel-title">Runtime Snapshot</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
- Indexed documents: `{collection_stats.document_count}`
- Available generation models: `{", ".join(config.model_options)}`
- Conversation turns used for follow-up resolution: `{config.conversation_history_turns}`
- Max context budget: `{config.max_context_chars}` characters
"""
    )
