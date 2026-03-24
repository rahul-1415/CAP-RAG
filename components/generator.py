# components/generator.py
import os
from functools import lru_cache


def truncate_context(content: str, max_chars: int) -> str:
    text = content or ""
    if len(text) > int(max_chars):
        return text[: int(max_chars)].rstrip()
    return text


def create_context_from_docs(docs, max_chars: int = None):
    """
    Join document content and trim to a reasonable character budget to avoid hitting TPM limits.
    """
    limit = int(max_chars or os.getenv("MAX_CONTEXT_CHARS", "15000"))
    content = " ".join([doc.page_content for doc in docs])
    return truncate_context(content, limit)


def _get_api_config():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    base_url = os.getenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")
    return api_key, base_url


@lru_cache(maxsize=4)
def _get_llm(model_name):
    from langchain_openai import ChatOpenAI

    api_key, base_url = _get_api_config()
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
    )


def generate_answer(context, question, model_name):
    """Generate an answer using the chosen Groq (OpenAI-compatible) chat model."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _get_llm(model_name)

    messages = [
        SystemMessage(
            content=(
                "You are a climate policy assistant. Answer using only the provided context. "
                "Cite factual claims with inline document IDs like [DOC_1] or [DOC_2]. "
                "Cite every bullet or factual paragraph. If the context is insufficient, say exactly what is missing. "
                "Do not mention any external sources or knowledge."
            )
        ),
        HumanMessage(
            content=(
                "Context documents:\n"
                f"{context}\n\n"
                "User question:\n"
                f"{question}\n\n"
                "Return a concise, well-structured answer with inline citations."
            )
        ),
    ]

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as exc:
        return (
            "I could not generate a response right now due to an upstream model error. "
            f"Details: {exc}"
        )


def run_refinement(model_name, system_prompt, user_prompt):
    """Run a constrained rewrite/refinement prompt with the selected model."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _get_llm(model_name)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return response.content
