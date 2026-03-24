import re
from typing import Iterable, List, Mapping


FOLLOW_UP_PATTERN = re.compile(
    r"\b("
    r"that|those|it|them|this|these|same|similar|compare|contrast|versus|vs|"
    r"what about|how about|and for|more on|expand|follow up|follow-up|barriers|risks|benefits"
    r")\b",
    re.IGNORECASE,
)


def _clean_message_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def format_recent_history(messages: Iterable[Mapping[str, str]], max_turns: int = 4, max_chars: int = 1200) -> str:
    items: List[str] = []
    recent_messages = [msg for msg in list(messages)[-max_turns * 2 :] if msg.get("content")]

    for message in recent_messages:
        role = "User" if message.get("role") == "user" else "Assistant"
        content = _clean_message_text(message.get("content", ""))
        if not content:
            continue
        items.append(f"{role}: {content[:260]}")

    history = "\n".join(items).strip()
    if len(history) > max_chars:
        history = history[-max_chars:].lstrip()
    return history


def looks_like_follow_up(question: str) -> bool:
    cleaned = _clean_message_text(question)
    if not cleaned:
        return False
    return len(cleaned.split()) <= 6 or bool(FOLLOW_UP_PATTERN.search(cleaned))


def build_retrieval_query(question: str, messages: Iterable[Mapping[str, str]], max_turns: int = 4) -> str:
    cleaned_question = _clean_message_text(question)
    if not cleaned_question:
        return ""

    if not looks_like_follow_up(cleaned_question):
        return cleaned_question

    prior_user_questions = []
    for message in reversed(list(messages)):
        if message.get("role") != "user":
            continue
        content = _clean_message_text(message.get("content", ""))
        if not content:
            continue
        prior_user_questions.append(content)
        if len(prior_user_questions) >= max_turns:
            break

    combined_parts = [cleaned_question] + list(reversed(prior_user_questions))
    deduped_parts: List[str] = []
    seen = set()
    for part in combined_parts:
        lowered = part.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped_parts.append(part)
    return " | ".join(deduped_parts)


def build_generation_question(question: str, messages: Iterable[Mapping[str, str]], max_turns: int = 4) -> str:
    cleaned_question = _clean_message_text(question)
    history = format_recent_history(messages, max_turns=max_turns)
    if not history:
        return cleaned_question

    return (
        "Use the recent conversation only to resolve references like pronouns or comparisons. "
        "Do not treat chat history as evidence.\n\n"
        f"Recent conversation:\n{history}\n\nCurrent question:\n{cleaned_question}"
    )
