# components/generator.py
import os
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def create_context_from_docs(docs):
    """
    Join document content and trim to a reasonable character budget to avoid hitting TPM limits.
    """
    max_chars = int(os.getenv("MAX_CONTEXT_CHARS", "15000"))
    content = " ".join([doc.page_content for doc in docs])
    if len(content) > max_chars:
        content = content[:max_chars]
    return content


def _get_api_config():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    base_url = os.getenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")
    return api_key, base_url


@lru_cache(maxsize=4)
def _get_llm(model_name):
    api_key, base_url = _get_api_config()
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
    )


def generate_answer(context, question, model_name):
    """Generate an answer using the chosen Groq (OpenAI-compatible) chat model."""
    llm = _get_llm(model_name)

    messages = [
        SystemMessage(
            content=(
                "You are a policy assistant. Answer using only the provided context. "
                "If the context is insufficient, say exactly what is missing."
            )
        ),
        HumanMessage(content=f"Context: {context}\n\nQuestion: {question}"),
    ]

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as exc:
        return (
            "I could not generate a response right now due to an upstream model error. "
            f"Details: {exc}"
        )
