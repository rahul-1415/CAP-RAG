import streamlit as st
from html import escape

from components.theme import current_theme_query_value


def _page_target(path: str) -> str:
    theme = current_theme_query_value()
    return f"{path}?theme={theme}"


def _render_nav_link(label: str, href: str, is_active: bool) -> None:
    safe_label = escape(label)
    safe_href = escape(href, quote=True)
    if is_active:
        st.markdown(f'<span class="top-nav-link active">{safe_label}</span>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<a class="top-nav-link" href="{safe_href}" target="_self">{safe_label}</a>',
            unsafe_allow_html=True,
        )


def _render_sidebar_link(label: str, href: str, is_active: bool) -> None:
    safe_label = escape(label)
    safe_href = escape(href, quote=True)
    if is_active:
        st.markdown(f'<span class="side-nav-link active">{safe_label}</span>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<a class="side-nav-link" href="{safe_href}" target="_self">{safe_label}</a>',
            unsafe_allow_html=True,
        )


def _render_sidebar(active_page: str) -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Menu</div>', unsafe_allow_html=True)
        _render_sidebar_link("Ask the Assistant", _page_target("/"), active_page == "chat")
        _render_sidebar_link("About This Project", _page_target("/About_This_Project"), active_page == "about")
        _render_sidebar_link("How It Works", _page_target("/How_It_Works"), active_page == "how_it_works")
        _render_sidebar_link("Analytics", _page_target("/Analytics"), active_page == "analytics")
        _render_sidebar_link("Settings", _page_target("/Settings"), active_page == "settings")
        st.markdown('<div class="sidebar-foot">C40 Climate Policy RAG</div>', unsafe_allow_html=True)


def render_top_nav(active_page: str) -> None:
    _render_sidebar(active_page)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        _render_nav_link("Ask the Assistant", _page_target("/"), active_page == "chat")
    with col2:
        _render_nav_link("About This Project", _page_target("/About_This_Project"), active_page == "about")
    with col3:
        _render_nav_link("How It Works", _page_target("/How_It_Works"), active_page == "how_it_works")
    with col4:
        _render_nav_link("Analytics", _page_target("/Analytics"), active_page == "analytics")
    with col5:
        _render_nav_link("Settings", _page_target("/Settings"), active_page == "settings")

    st.divider()
