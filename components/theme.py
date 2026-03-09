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
            "bg_main": "#0b1318",
            "bg_accent": "#0f3342",
            "surface_1": "#132129",
            "surface_2": "#1c2f39",
            "text_main": "#e7f1f6",
            "text_muted": "#a7bcc7",
            "border": "#304a56",
            "accent": "#35b68f",
            "shadow": "rgba(0, 0, 0, 0.35)",
            "metric_text": "#e7f1f6",
            "toggle_knob": "#e7f1f6",
            "toggle_border": "#304a56",
        }
    else:
        tokens = {
            "bg_main": "#f3f6f9",
            "bg_accent": "#d9e6ef",
            "surface_1": "#ffffff",
            "surface_2": "#edf2f7",
            "text_main": "#111827",
            "text_muted": "#425466",
            "border": "#111827",
            "accent": "#0f766e",
            "shadow": "rgba(17, 24, 39, 0.10)",
            "metric_text": "#111827",
            "toggle_knob": "#111827",
            "toggle_border": "#000000",
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
            --toggle-border: {tokens["toggle_border"]};
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
            padding-left: 1.2rem;
            padding-right: 1.2rem;
            max-width: 100% !important;
            animation: fadeIn 220ms ease;
        }}

        [data-testid="stSidebar"] {{
            background: var(--surface-1);
            border-right: 1px solid var(--border);
        }}

        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding-top: 1rem;
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

        .panel-title {{
            font-family: 'Manrope', sans-serif !important;
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: var(--text-main) !important;
            margin: 0.15rem 0 0.45rem 0;
        }}

        .app-main-title {{
            font-family: 'Manrope', sans-serif !important;
            font-size: clamp(1.85rem, 2.6vw, 2.35rem);
            line-height: 1.05;
            letter-spacing: -0.02em;
            color: var(--text-main) !important;
            margin: 0.1rem 0 0.35rem 0;
            white-space: nowrap;
        }}

        .section-kicker {{
            font-family: 'Manrope', sans-serif !important;
            color: var(--text-muted) !important;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }}

        .chat-current {{
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface-2);
            padding: 0.55rem 0.8rem;
            margin: 0.3rem 0 0.65rem 0;
            font-family: 'Manrope', sans-serif !important;
            font-weight: 600;
            color: var(--text-main) !important;
        }}

        .control-label {{
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-main) !important;
            margin-bottom: 0.2rem;
            text-align: center;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label) {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stSelectbox"],
        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stNumberInput"] {{
            width: 100%;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stSelectbox"] > div,
        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stNumberInput"] > div {{
            margin-left: auto;
            margin-right: auto;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stCheckbox"] {{
            width: 100%;
            display: flex;
            justify-content: center;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label) [data-testid="stCheckbox"] > label {{
            margin-left: auto;
            margin-right: auto;
        }}

        [data-testid="stHorizontalBlock"] > div:has(.control-label)
        label[data-baseweb="checkbox"]:has(input[aria-label="Reranking"]) {{
            width: 100% !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
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

        .menu-bar-title {{
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--text-muted) !important;
            margin-bottom: 0.55rem;
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

        .sidebar-title {{
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.84rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--text-muted) !important;
            margin: 0.2rem 0 0.45rem 0;
        }}

        .side-nav-link, .side-nav-link:visited {{
            display: block;
            width: 100%;
            text-decoration: none;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface-1);
            color: var(--text-main) !important;
            padding: 0.58rem 0.72rem;
            margin-bottom: 0.42rem;
            box-shadow: 0 5px 12px var(--shadow);
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
        }}

        .side-nav-link:hover {{
            border-color: var(--accent);
            background: var(--surface-2);
            transform: translateY(-1px);
        }}

        .side-nav-link.active {{
            background: var(--surface-2);
            cursor: default;
            pointer-events: none;
        }}

        .sidebar-foot {{
            margin-top: 0.75rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted) !important;
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.01em;
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

        [data-testid="stRadio"] > div,
        [data-testid="stSelectbox"] > div[data-baseweb="select"],
        [data-testid="stNumberInput"] > div[data-baseweb="input"] {{
            background: var(--surface-1) !important;
            border-color: var(--border) !important;
        }}

        [data-testid="stCheckbox"] {{
            padding-top: 0.05rem;
        }}

        label[data-baseweb="checkbox"]:has(input[aria-label="Reranking"]) > div:first-child {{
            border: 2px solid var(--toggle-border) !important;
        }}

        label[data-baseweb="checkbox"]:has(input[aria-label="Reranking"]) > div:first-child > div {{
            border: 1px solid var(--toggle-border) !important;
        }}

        [data-testid="stRadio"] label p,
        [data-testid="stSelectbox"] label p,
        [data-testid="stNumberInput"] label p {{
            font-family: 'Manrope', sans-serif !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            color: var(--text-main) !important;
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
            .app-main-title {{
                white-space: normal;
                font-size: 2rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
