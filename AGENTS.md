# AGENTS.md

This file defines project-specific rules for AI coding agents working in this repository.

## Project Summary

CAP-RAG is a Streamlit Retrieval-Augmented Generation app for climate policy Q&A.

- Primary source corpus: https://www.c40knowledgehub.org/
- Retriever: Chroma + HuggingFace embeddings (`BAAI/bge-small-en-v1.5`)
- Generator: Groq OpenAI-compatible chat models
- Main entrypoint: `app.py`
- Extra pages: `pages/1_About_This_Project.py`, `pages/2_How_It_Works.py`

## Environment and Run

Use the repo-local `.venv` by default.

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

## Non-Negotiable Content Rules

- Do not label evidence as "Unknown source".
- If source metadata is missing, fall back to `https://www.c40knowledgehub.org/`.
- Keep About/How-It-Works page copy aligned with actual app behavior.

## App Behavior Requirements

- Theme must persist across tab/page navigation.
- Theme query parameter is `theme` (`light` or `dark`); preserve this behavior.
- Top navigation uses custom links in `components/navigation.py` (do not regress to broken links).
- Keep dark mode toggle placement consistent across pages.
- Chat naming defaults to ordinal naming (`My first chat`, `My second chat`, etc.).
- Users must be able to create a new chat before asking a question.

## Retrieval and Generation Rules

- Keep retriever initialization cached via `@st.cache_resource`.
- Respect user-selected retrieval depth (`Documents to check`, default `5`).
- Retrieval depth is controlled in session state key `retrieval_k`.
- If changing retrieval logic, ensure `k` is configurable per query and does not break MMR behavior.
- Keep context-size guard via `MAX_CONTEXT_CHARS`.

## File Ownership and Responsibilities

- `app.py`: chat flow, controls, session state, retrieval/generation orchestration.
- `components/retriever.py`: embedding model + Chroma retriever setup.
- `components/generator.py`: Groq model setup and answer generation.
- `components/reranker.py`: reranker adapters and fallback behavior.
- `components/postprocessor.py`: rule/LLM post-processing utilities.
- `components/rag_pipeline.py`: orchestration of retrieve -> rerank -> postprocess -> generate.
- `components/analytics_store.py`: persistent SQLite metrics logging and reads.
- `components/rag_config.py`: environment/runtime knobs for advanced RAG.
- `components/theme.py`: theme state/query sync and CSS tokens.
- `components/navigation.py`: top tab links + theme propagation.
- `pages/*.py`: product/content documentation tabs shown inside app.

## UI / UX Guardrails

- Preserve Manrope + Merriweather typography.
- In light mode, borders and key text must remain clearly visible (dark/black contrast).
- Do not introduce fixed-position dark mode controls unless explicitly requested.
- Keep chat input near conversation context (not detached from chat area).

## Safety and Secrets

- Never commit secrets from `.env` (especially `GROQ_API_KEY`).
- Avoid printing raw API keys in logs, errors, or generated docs.

## Validation Before Finishing Changes

Run at least:

```bash
python -m compileall app.py components pages
```

If UI/navigation/theme changes were made, also manually verify:

1. Dark mode toggle updates theme and persists after tab switch.
2. Top nav links work for all pages.
3. Chat input and chat history render correctly in light and dark themes.
