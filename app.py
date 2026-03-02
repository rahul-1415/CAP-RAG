from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from components.generator import create_context_from_docs, generate_answer
from components.navigation import render_top_nav
from components.retriever import initialize_retriever
from components.theme import apply_theme_styles, init_theme_state, render_dark_mode_slider

# Explicitly point to .env file in the project root.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

st.set_page_config(page_title="Climate Policy RAG", page_icon=":earth_americas:", layout="wide")


@st.cache_resource(show_spinner=False)
def get_retriever():
    return initialize_retriever()


def _format_chat_title(text: str, fallback: str = "Untitled chat") -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return fallback
    return cleaned[:64] + ("..." if len(cleaned) > 64 else "")


def _source_label(metadata, idx):
    source = (
        metadata.get("source")
        or metadata.get("url")
        or metadata.get("file_path")
        or "https://www.c40knowledgehub.org/"
    )
    page = metadata.get("page")
    if page is not None:
        return f"Doc {idx}: {source} (page {page})"
    return f"Doc {idx}: {source}"


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
    return {"id": uuid4().hex, "title": resolved_title, "messages": messages, "latest_docs": []}


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
        st.session_state.model_choice = "llama-3.3-70b-versatile"

    if "chats" not in st.session_state:
        chats = _migrate_legacy_state()
        if not chats:
            chats = [_create_chat(title=_default_chat_title(1))]
        st.session_state.chats = chats

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]

    active_exists = any(chat["id"] == st.session_state.active_chat_id for chat in st.session_state.chats)
    if not active_exists:
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]


def _get_active_chat():
    for chat in st.session_state.chats:
        if chat["id"] == st.session_state.active_chat_id:
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
            _process_prompt(suggestion, st.session_state.model_choice)
            st.rerun()


def _process_prompt(prompt, model_name):
    active_chat = _get_active_chat()
    active_chat["messages"].append({"role": "user", "content": prompt})

    try:
        with st.spinner("Retrieving policy context..."):
            retriever = get_retriever()
            retrieved_docs = retriever.invoke(prompt)
    except Exception as exc:
        active_chat["latest_docs"] = []
        active_chat["messages"].append({"role": "assistant", "content": f"Retriever failed: {exc}"})
        return

    active_chat["latest_docs"] = [
        {"source": _source_label(doc.metadata or {}, idx), "text": doc.page_content[:800]}
        for idx, doc in enumerate(retrieved_docs, start=1)
    ]

    context = create_context_from_docs(retrieved_docs)
    if not context.strip():
        answer = (
            "I could not find relevant policy context for that query. "
            "Try adding more specific details (policy name, region, or year)."
        )
    else:
        with st.spinner("Generating response..."):
            answer = generate_answer(context, prompt, model_name)

    active_chat["messages"].append({"role": "assistant", "content": answer})


_init_session_state()
init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_dark_mode_slider()
render_top_nav(active_page="chat")

col1, col2 = st.columns([1, 2.6], gap="large")

with col1:
    with st.container(border=True):
        st.title("Chats")
        st.button("New Chat", on_click=create_new_chat, use_container_width=True, type="primary")
        st.markdown(
            '<p class="chat-caption">Default names use chat order. You can rename any active chat.</p>',
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

    header_col1, header_col2 = st.columns([2.1, 1.4], gap="medium")
    with header_col1:
        st.title("Climate Policy RAG Assistant")
        st.caption("Ask policy questions grounded in the C40 Knowledge Hub dataset.")
    with header_col2:
        st.radio(
            "Model",
            options=["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
            key="model_choice",
            horizontal=True,
        )
    st.markdown(f"**Current chat:** `{active_chat['title']}`")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Chats", str(len(st.session_state.chats)))
    metric_col2.metric("Replies", str(_assistant_reply_count(active_chat)))
    metric_col3.metric("Evidence", str(len(active_chat["latest_docs"])))

    if active_chat["latest_docs"]:
        with st.expander("Retrieved evidence from latest question", expanded=False):
            for doc in active_chat["latest_docs"]:
                st.caption(doc["source"])
                st.markdown(doc["text"])
                st.divider()

    chat_container = st.container(border=True)
    with chat_container:
        if not active_chat["messages"]:
            st.info("Start a new conversation by asking a climate policy question.")
            st.markdown(
                """
Try prompts like:
- "How can a city decarbonise urban freight quickly?"
- "What are practical steps for climate budgeting in city government?"
- "Which actions improve air quality and reduce emissions together?"
"""
            )
            _render_quick_prompts(active_chat)
        else:
            for message in active_chat["messages"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    prompt = st.chat_input("Enter your query")
    if prompt:
        _process_prompt(prompt, st.session_state.model_choice)
        st.rerun()
