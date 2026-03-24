import json
from pathlib import Path
from typing import Dict
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as st_components
from dotenv import load_dotenv

from components.analytics_store import AnalyticsStore
from components.navigation import render_top_nav
from components.rag_config import (
    POSTPROCESS_MODES,
    init_advanced_rag_session_state,
    load_rag_runtime_config,
)
from components.rag_pipeline import run_pipeline
from components.retriever import initialize_retriever
from components.theme import apply_theme_styles, init_theme_state

# Explicitly point to .env file in the project root.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

st.set_page_config(page_title="Climate Policy RAG", page_icon=":earth_americas:", layout="wide")
APP_CONFIG = load_rag_runtime_config()
MODEL_OPTIONS = list(APP_CONFIG.model_options)


@st.cache_resource(show_spinner=False)
def get_retriever():
    return initialize_retriever()


@st.cache_resource(show_spinner=False)
def get_analytics_store(db_path: str, enabled: bool):
    return AnalyticsStore(Path(db_path), enabled=enabled)


def _format_chat_title(text: str, fallback: str = "Untitled chat") -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return fallback
    return cleaned[:64] + ("..." if len(cleaned) > 64 else "")


def _ordinal_label(number: int) -> str:
    ordinal_words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
        11: "eleventh",
        12: "twelfth",
        13: "thirteenth",
        14: "fourteenth",
        15: "fifteenth",
        16: "sixteenth",
        17: "seventeenth",
        18: "eighteenth",
        19: "nineteenth",
        20: "twentieth",
    }
    if number in ordinal_words:
        return ordinal_words[number]

    suffix = "th"
    if number % 100 not in {11, 12, 13}:
        if number % 10 == 1:
            suffix = "st"
        elif number % 10 == 2:
            suffix = "nd"
        elif number % 10 == 3:
            suffix = "rd"
    return f"{number}{suffix}"


def _default_chat_title(chat_number: int) -> str:
    return f"My {_ordinal_label(chat_number)} chat"


def _create_chat(messages=None, title=None):
    messages = messages or []
    if title:
        resolved_title = _format_chat_title(title, fallback="Untitled chat")
    else:
        resolved_title = "Untitled chat"
        for message in messages:
            if message.get("role") == "user" and message.get("content", "").strip():
                resolved_title = _format_chat_title(message["content"], fallback="Untitled chat")
                break
    return {
        "id": uuid4().hex,
        "title": resolved_title,
        "messages": messages,
        "latest_docs": [],
        "latest_notes": [],
        "latest_metrics": {},
        "latest_run_id": None,
    }


def _migrate_legacy_state():
    chats = []
    legacy_current = st.session_state.get("current_chat") or []
    legacy_all = st.session_state.get("all_chats") or []

    if legacy_current:
        chats.append(_create_chat(messages=list(legacy_current)))
    for legacy_chat in legacy_all:
        chats.append(_create_chat(messages=list(legacy_chat)))
    return chats


def _init_session_state():
    if "model_choice" not in st.session_state:
        st.session_state.model_choice = MODEL_OPTIONS[0]
    if st.session_state.model_choice not in MODEL_OPTIONS:
        st.session_state.model_choice = MODEL_OPTIONS[0]

    if "retrieval_k" not in st.session_state:
        st.session_state.retrieval_k = 5

    init_advanced_rag_session_state(
        session_state=st.session_state,
        config=APP_CONFIG,
        default_model=st.session_state.model_choice,
    )

    if st.session_state.postprocess_mode not in POSTPROCESS_MODES:
        st.session_state.postprocess_mode = APP_CONFIG.postprocess_mode_default
    if st.session_state.postprocess_model_choice not in MODEL_OPTIONS:
        st.session_state.postprocess_model_choice = st.session_state.model_choice

    if "chats" not in st.session_state:
        chats = _migrate_legacy_state()
        if not chats:
            chats = [_create_chat(title=_default_chat_title(1))]
        st.session_state.chats = chats

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]

    for chat in st.session_state.chats:
        chat.setdefault("latest_docs", [])
        chat.setdefault("latest_notes", [])
        chat.setdefault("latest_metrics", {})
        chat.setdefault("latest_run_id", None)

    active_exists = any(chat["id"] == st.session_state.active_chat_id for chat in st.session_state.chats)
    if not active_exists:
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]


def _get_active_chat():
    for chat in st.session_state.chats:
        if chat["id"] == st.session_state.active_chat_id:
            chat.setdefault("latest_docs", [])
            chat.setdefault("latest_notes", [])
            chat.setdefault("latest_metrics", {})
            chat.setdefault("latest_run_id", None)
            return chat
    st.session_state.active_chat_id = st.session_state.chats[0]["id"]
    return st.session_state.chats[0]


def create_new_chat():
    chat_number = len(st.session_state.chats) + 1
    new_chat = _create_chat(title=_default_chat_title(chat_number))
    st.session_state.chats.insert(0, new_chat)
    st.session_state.active_chat_id = new_chat["id"]


def _assistant_reply_count(chat):
    return sum(1 for message in chat["messages"] if message.get("role") == "assistant")


def _latest_run_message(chat):
    for message in reversed(chat["messages"]):
        if message.get("role") == "assistant" and (
            message.get("run_id") or message.get("evidence_docs") or message.get("timings")
        ):
            return message
    return None


def _render_quick_prompts(chat):
    suggestions = [
        "How can a city decarbonise urban freight quickly?",
        "What are practical steps for climate budgeting in city government?",
        "Which actions improve air quality and reduce emissions together?",
        "How should a city start an extreme heat adaptation plan?",
    ]

    row1, row2 = st.columns(2, gap="small")
    prompt_columns = [row1, row2, row1, row2]

    for idx, suggestion in enumerate(suggestions):
        button_key = f"quick_prompt_{chat['id']}_{idx}"
        if prompt_columns[idx].button(suggestion, key=button_key, use_container_width=True):
            _process_prompt(suggestion)
            st.rerun()


def _process_prompt(prompt: str) -> None:
    active_chat = _get_active_chat()
    history_messages = list(active_chat["messages"])
    active_chat["messages"].append({"role": "user", "content": prompt})

    try:
        retriever = get_retriever()
        analytics_store = get_analytics_store(str(APP_CONFIG.analytics_db_path), APP_CONFIG.enable_analytics)
        analytics_store.apply_retention(
            max_days=APP_CONFIG.analytics_retention_days,
            max_rows=APP_CONFIG.analytics_retention_rows,
        )
    except Exception as exc:
        active_chat["latest_docs"] = []
        active_chat["latest_notes"] = [f"Runtime initialization failed: {exc}"]
        active_chat["latest_metrics"] = {}
        active_chat["messages"].append(
            {
                "role": "assistant",
                "content": f"Retriever failed: {exc}",
                "run_id": None,
                "evidence_docs": [],
                "warnings": active_chat["latest_notes"],
                "timings": {},
            }
        )
        return

    with st.spinner("Running advanced RAG pipeline..."):
        result = run_pipeline(
            query=prompt,
            generation_model=st.session_state.model_choice,
            retrieval_k=int(st.session_state.retrieval_k),
            rerank_enabled=bool(st.session_state.rerank_enabled),
            postprocess_mode=st.session_state.postprocess_mode,
            postprocess_model=st.session_state.postprocess_model_choice,
            retriever=retriever,
            config=APP_CONFIG,
            analytics_store=analytics_store,
            conversation_messages=history_messages,
        )

    active_chat["latest_docs"] = result.get("evidence_docs", [])
    active_chat["latest_notes"] = result.get("warnings", [])
    active_chat["latest_metrics"] = result.get("timings", {})
    active_chat["latest_run_id"] = result.get("run_id")
    active_chat["messages"].append(
        {
            "role": "assistant",
            "content": result.get("answer", ""),
            "run_id": result.get("run_id"),
            "evidence_docs": result.get("evidence_docs", []),
            "warnings": result.get("warnings", []),
            "timings": result.get("timings", {}),
        }
    )


def _open_external_url(url: str) -> None:
    if not url:
        return
    safe_url = json.dumps(url)
    st_components.html(
        f"<script>window.open({safe_url}, '_blank', 'noopener,noreferrer');</script>",
        height=0,
        width=0,
    )


def _log_feedback(run_id: str, feedback_type: str) -> None:
    if not run_id:
        return
    try:
        analytics_store = get_analytics_store(str(APP_CONFIG.analytics_db_path), APP_CONFIG.enable_analytics)
        analytics_store.log_feedback(run_id=run_id, feedback_type=feedback_type)
    except Exception:
        pass


def _log_source_click(run_id: str, doc: Dict[str, str], position: int) -> None:
    if not run_id:
        return
    try:
        analytics_store = get_analytics_store(str(APP_CONFIG.analytics_db_path), APP_CONFIG.enable_analytics)
        analytics_store.log_source_click(
            run_id=run_id,
            doc_id=doc.get("doc_id"),
            source=doc.get("source"),
            title=doc.get("title"),
            position=position,
        )
    except Exception:
        pass


def _render_answer_feedback(run_id: str) -> None:
    rating_state_key = f"feedback_rating_{run_id}"
    missing_evidence_key = f"feedback_missing_evidence_{run_id}"
    rating_submitted = st.session_state.get(rating_state_key)
    missing_evidence_submitted = bool(st.session_state.get(missing_evidence_key, False))

    feedback_col1, feedback_col2, feedback_col3 = st.columns(3)
    if feedback_col1.button(
        "Helpful",
        key=f"feedback_helpful_{run_id}",
        use_container_width=True,
        disabled=rating_submitted is not None,
    ):
        _log_feedback(run_id, "helpful")
        st.session_state[rating_state_key] = "helpful"
        st.rerun()
    if feedback_col2.button(
        "Needs work",
        key=f"feedback_not_helpful_{run_id}",
        use_container_width=True,
        disabled=rating_submitted is not None,
    ):
        _log_feedback(run_id, "not_helpful")
        st.session_state[rating_state_key] = "not_helpful"
        st.rerun()
    if feedback_col3.button(
        "Missing evidence",
        key=f"feedback_missing_evidence_button_{run_id}",
        use_container_width=True,
        disabled=missing_evidence_submitted,
    ):
        _log_feedback(run_id, "missing_evidence")
        st.session_state[missing_evidence_key] = True
        st.rerun()

    if rating_submitted == "helpful":
        st.caption("Feedback saved: helpful.")
    elif rating_submitted == "not_helpful":
        st.caption("Feedback saved: needs work.")
    if missing_evidence_submitted:
        st.caption("Feedback saved: missing evidence flagged.")


def _render_message_evidence(message: Dict[str, object]) -> None:
    evidence_docs = message.get("evidence_docs") or []
    warnings = message.get("warnings") or []
    timings = message.get("timings") or {}
    run_id = message.get("run_id")

    if not evidence_docs and not warnings and not timings and not run_id:
        return

    with st.expander("Sources and run details", expanded=False):
        if warnings:
            for note in warnings:
                st.caption(f"Note: {note}")

        if timings:
            st.caption(
                "Timings (ms): "
                f"retrieve={timings.get('retrieval_ms', 0):.0f}, "
                f"rerank={timings.get('rerank_ms', 0):.0f}, "
                f"generate={timings.get('generation_ms', 0):.0f}, "
                f"post={timings.get('postprocess_ms', 0):.0f}"
            )

        if run_id:
            _render_answer_feedback(run_id)

        for position, doc in enumerate(evidence_docs, start=1):
            header_col, action_col = st.columns([3.2, 1], gap="small")
            header_col.markdown(f"**{doc.get('doc_id', f'Doc {position}')}** · {doc.get('title', 'C40 document')}")
            if action_col.button(
                "Open source",
                key=f"open_source_{run_id}_{doc.get('doc_id', position)}",
                use_container_width=True,
            ):
                _log_source_click(run_id, doc, position)
                _open_external_url(doc.get("source", ""))
            st.caption(doc.get("source", ""))
            st.markdown(doc.get("text", ""))
            st.divider()


def _postprocess_label(mode: str) -> str:
    mapping = {
        "none": "None",
        "rules_only": "Rules Only",
        "rules_plus_llm": "Rules + LLM",
    }
    return mapping.get(mode, mode)


_init_session_state()
init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_top_nav(active_page="chat")

col1, col2 = st.columns([1, 2.6], gap="large")

with col1:
    with st.container(border=True):
        st.title("Chats")
        st.button("New Chat", on_click=create_new_chat, use_container_width=True, type="primary")
        st.markdown(
            '<div class="panel-title">Chat History</div>',
            unsafe_allow_html=True,
        )

        for chat in st.session_state.chats:
            is_active = chat["id"] == st.session_state.active_chat_id
            if st.button(
                chat["title"],
                key=f"chat_{chat['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_chat_id = chat["id"]
                st.rerun()

        st.divider()
        active_chat_for_sidebar = _get_active_chat()
        rename_key = f"rename_title_{active_chat_for_sidebar['id']}"
        if rename_key not in st.session_state:
            st.session_state[rename_key] = active_chat_for_sidebar["title"]

        st.text_input("Rename active chat", key=rename_key, placeholder="Enter chat title")
        if st.button("Save Title", key=f"save_title_{active_chat_for_sidebar['id']}", use_container_width=True):
            active_chat_for_sidebar["title"] = _format_chat_title(
                st.session_state[rename_key],
                fallback=active_chat_for_sidebar["title"],
            )
            st.session_state[rename_key] = active_chat_for_sidebar["title"]
            st.rerun()

with col2:
    active_chat = _get_active_chat()

    with st.container(border=True):
        st.markdown('<h1 class="app-main-title">Climate Policy RAG Assistant</h1>', unsafe_allow_html=True)
        st.caption("Ask policy questions grounded in the C40 Knowledge Hub dataset.")

        controls_col1, controls_col2, controls_col3, controls_col4, controls_col5 = st.columns(
            [1.35, 1.0, 0.9, 1.2, 1.2], gap="small"
        )
        with controls_col1:
            st.markdown('<div class="control-label">Choose model</div>', unsafe_allow_html=True)
            st.selectbox(
                "Choose model",
                options=MODEL_OPTIONS,
                key="model_choice",
                label_visibility="collapsed",
            )
        with controls_col2:
            st.markdown('<div class="control-label">Documents to check</div>', unsafe_allow_html=True)
            st.number_input(
                "Documents to check",
                min_value=1,
                max_value=20,
                step=1,
                key="retrieval_k",
                label_visibility="collapsed",
                help="Controls final number of chunks selected for answering.",
            )
        with controls_col3:
            st.markdown('<div class="control-label">Reranking</div>', unsafe_allow_html=True)
            rerank_pad_left, rerank_toggle_col, rerank_pad_right = st.columns([1, 1, 1], gap="small")
            with rerank_toggle_col:
                st.toggle(
                    "Reranking",
                    key="rerank_enabled",
                    label_visibility="collapsed",
                    help="Use Cohere reranking on retrieved chunks before answer generation.",
                )
        with controls_col4:
            st.markdown('<div class="control-label">Post-processing</div>', unsafe_allow_html=True)
            st.selectbox(
                "Post-processing",
                options=list(POSTPROCESS_MODES),
                key="postprocess_mode",
                label_visibility="collapsed",
                format_func=_postprocess_label,
            )
        with controls_col5:
            st.markdown('<div class="control-label">Post-process LLM</div>', unsafe_allow_html=True)
            st.selectbox(
                "Post-process LLM",
                options=MODEL_OPTIONS,
                key="postprocess_model_choice",
                disabled=st.session_state.postprocess_mode != "rules_plus_llm",
                label_visibility="collapsed",
                help="Used only when post-processing mode is Rules + LLM.",
            )

        st.markdown(f'<div class="chat-current">Current chat: {active_chat["title"]}</div>', unsafe_allow_html=True)

    latest_run = _latest_run_message(active_chat) or {}
    latest_metrics: Dict[str, float] = active_chat.get("latest_metrics", {}) or latest_run.get("timings", {}) or {}
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Chats", str(len(st.session_state.chats)))
    metric_col2.metric("Replies", str(_assistant_reply_count(active_chat)))
    metric_col3.metric("Evidence", str(len(active_chat.get("latest_docs", []) or latest_run.get("evidence_docs", []))))
    metric_col4.metric("Last Latency", f"{int(latest_metrics.get('total_ms', 0))} ms")

    if active_chat.get("latest_docs"):
        with st.expander("Retrieved evidence from latest question", expanded=False):
            if active_chat.get("latest_notes"):
                for note in active_chat["latest_notes"]:
                    st.caption(f"Note: {note}")

            if latest_metrics:
                st.caption(
                    "Timings (ms): "
                    f"retrieve={latest_metrics.get('retrieval_ms', 0):.0f}, "
                    f"rerank={latest_metrics.get('rerank_ms', 0):.0f}, "
                    f"generate={latest_metrics.get('generation_ms', 0):.0f}, "
                    f"post={latest_metrics.get('postprocess_ms', 0):.0f}"
                )
            for doc in active_chat["latest_docs"]:
                st.caption(doc["source"])
                st.markdown(doc["text"])
                st.divider()

    chat_container = st.container(border=True)
    with chat_container:
        if not active_chat["messages"]:
            st.info("Start a new conversation by asking a climate policy question.")
            st.markdown("Try prompts like:")
            _render_quick_prompts(active_chat)
        else:
            for message in active_chat["messages"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if message.get("role") == "assistant":
                        _render_message_evidence(message)

    prompt = st.chat_input("Enter your query")
    if prompt:
        _process_prompt(prompt)
        st.rerun()
