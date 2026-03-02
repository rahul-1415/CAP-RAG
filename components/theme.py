import streamlit as st
from typing import Optional

THEME_QUERY_PARAM = "theme"


def _query_param_value(name: str) -> Optional[str]:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _parse_theme_param(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"dark", "true", "1", "on"}:
        return True
    if normalized in {"light", "false", "0", "off"}:
        return False
    return None


def current_theme_query_value() -> str:
    return "dark" if bool(st.session_state.get("dark_mode", False)) else "light"


def sync_theme_query_param() -> None:
    desired = current_theme_query_value()
    current = _query_param_value(THEME_QUERY_PARAM)
    if current != desired:
        st.query_params[THEME_QUERY_PARAM] = desired


def init_theme_state(default_dark_mode: bool = False) -> None:
    query_theme = _parse_theme_param(_query_param_value(THEME_QUERY_PARAM))

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = default_dark_mode if query_theme is None else query_theme

    sync_theme_query_param()


def render_dark_mode_slider() -> None:
    st.toggle("Dark mode", key="dark_mode", help="Switch between light and dark themes.")
    sync_theme_query_param()


def apply_theme_styles() -> None:
    dark_mode = bool(st.session_state.get("dark_mode", False))

    if dark_mode:
        tokens = {
            "bg_main": "#0c1418",
            "bg_accent": "#123844",
            "surface_1": "#122127",
            "surface_2": "#1a2d35",
            "text_main": "#e9f5f7",
            "text_muted": "#abc2ca",
            "border": "#35515c",
            "accent": "#4ec9a4",
            "shadow": "rgba(0, 0, 0, 0.35)",
            "metric_text": "#e9f5f7",
            "toggle_knob": "#e9f5f7",
        }
    else:
        tokens = {
            "bg_main": "#eaf2ef",
            "bg_accent": "#bfded2",
            "surface_1": "#ffffff",
            "surface_2": "#e4efea",
            "text_main": "#10212a",
            "text_muted": "#38505c",
            "border": "#000000",
            "accent": "#0a7a5d",
            "shadow": "rgba(20, 45, 56, 0.10)",
            "metric_text": "#000000",
            "toggle_knob": "#000000",
        }

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Merriweather:wght@400;700&display=swap');

        :root {{
            --bg-main: {tokens["bg_main"]};
            --bg-accent: {tokens["bg_accent"]};
            --surface-1: {tokens["surface_1"]};
            --surface-2: {tokens["surface_2"]};
            --text-main: {tokens["text_main"]};
            --text-muted: {tokens["text_muted"]};
            --border: {tokens["border"]};
            --accent: {tokens["accent"]};
            --shadow: {tokens["shadow"]};
            --metric-text: {tokens["metric_text"]};
            --toggle-knob: {tokens["toggle_knob"]};
        }}

        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 0% -10%, var(--bg-accent) 0%, var(--bg-main) 34%, var(--bg-main) 100%),
                linear-gradient(130deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0) 60%);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        .block-container {{
            padding-top: 4.2rem;
            padding-bottom: 1.2rem;
            max-width: 1380px;
            animation: fadeIn 220ms ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(3px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        h1, h2, h3, h4 {{
            font-family: 'Manrope', sans-serif !important;
            color: var(--text-main) !important;
            letter-spacing: -0.02em;
        }}

        p, li, label, code, input, textarea {{
            color: var(--text-main);
            font-family: 'Merriweather', serif !important;
        }}

        .stCaption, .chat-caption {{
            color: var(--text-muted) !important;
        }}

        .stMarkdown p, .stMarkdown li, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
            font-family: 'Merriweather', serif !important;
        }}

        [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] *, [data-testid="stMetricLabel"] * {{
            color: var(--metric-text) !important;
        }}

        a[data-testid="stPageLink-NavLink"] {{
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface-1);
            box-shadow: 0 6px 14px var(--shadow);
        }}

        a[data-testid="stPageLink-NavLink"]:hover {{
            border-color: var(--accent);
            transform: translateY(-1px);
        }}

        .top-nav-link, .top-nav-link:visited {{
            display: block;
            width: 100%;
            text-align: center;
            text-decoration: none;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface-1);
            color: var(--text-main) !important;
            padding: 0.6rem 0.8rem;
            box-shadow: 0 6px 14px var(--shadow);
            font-family: 'Manrope', sans-serif !important;
            font-weight: 700;
            letter-spacing: -0.01em;
            transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
        }}

        .top-nav-link:hover {{
            border-color: var(--accent);
            background: var(--surface-2);
            transform: translateY(-1px);
        }}

        .top-nav-link.active {{
            background: var(--surface-2);
            cursor: default;
            pointer-events: none;
        }}

        [data-testid="stVerticalBlock"], [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--border) !important;
        }}

        [data-testid="stVerticalBlock"][style*="border"], [data-testid="stVerticalBlockBorderWrapper"] {{
            border-width: 2px !important;
            border-color: var(--border) !important;
            background: var(--surface-1);
            box-shadow: 0 8px 20px var(--shadow);
            border-radius: 18px;
        }}

        hr, [data-testid="stDivider"] {{
            border-color: var(--border) !important;
        }}

        div[data-testid="stChatMessage"] {{
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.25rem 0.85rem;
            margin-bottom: 0.75rem;
        }}

        div[data-testid="stButton"] > button {{
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface-1);
            color: var(--text-main);
            transition: all 0.18s ease;
            box-shadow: 0 4px 10px var(--shadow);
        }}

        div[data-testid="stButton"] > button:hover {{
            border-color: var(--accent);
            background: var(--surface-2);
            transform: translateY(-1px);
        }}

        [data-testid="stTextInput"] input, textarea {{
            background: var(--surface-1) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
        }}

        [data-testid="stChatInput"] {{
            margin-top: 0.75rem;
            padding: 0.45rem 0.5rem;
            background: var(--surface-1);
            border: 2px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 6px 14px var(--shadow);
        }}

        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="base-input"] {{
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }}

        [data-testid="stChatInputTextArea"] {{
            font-family: 'Merriweather', serif !important;
            font-size: 1rem !important;
            line-height: 1.35 !important;
        }}

        [data-testid="stChatInputSubmitButton"] {{
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            background: var(--surface-2) !important;
            color: var(--text-main) !important;
        }}

        [data-testid="stChatInputSubmitButton"]:hover:not(:disabled) {{
            border-color: var(--accent) !important;
            background: var(--surface-1) !important;
        }}

        label[data-baseweb="checkbox"]:has(input[aria-label="Dark mode"]) {{
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.38rem 0.6rem;
            box-shadow: 0 4px 10px var(--shadow);
        }}

        label[data-baseweb="checkbox"]:has(input[aria-label="Dark mode"]) > div:first-child {{
            border: 1px solid var(--border) !important;
        }}

        label[data-baseweb="checkbox"]:has(input[aria-label="Dark mode"]) > div:first-child > div {{
            background: var(--toggle-knob) !important;
            border: 1px solid var(--border) !important;
        }}

        [data-testid="stAlert"], [data-testid="stExpander"] {{
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: 12px;
        }}

        [data-testid="stMetric"] {{
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.35rem 0.75rem;
            box-shadow: 0 6px 16px var(--shadow);
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-top: 3.3rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }}
            h1 {{
                font-size: 1.55rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
