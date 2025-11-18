# components/generator.py
import os

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


def generate_answer(context, question, model_name):
    """Generate an answer using the chosen Groq (OpenAI-compatible) chat model."""
    api_key, base_url = _get_api_config()

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
    )

    messages = [
        SystemMessage(content="Answer the question using only the provided context."),
        HumanMessage(content=f"Context: {context}\n\nQuestion: {question}"),
    ]

    response = llm.invoke(messages)
    return response.content
