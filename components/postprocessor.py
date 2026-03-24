import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from components.document_utils import SOURCE_FALLBACK, extract_doc_title, metadata_source, normalize_text
from components.generator import run_refinement


@dataclass
class ProcessedDoc:
    doc_id: str
    title: str
    source: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class PostprocessDocsOutput:
    docs: List[ProcessedDoc]
    context: str
    notes: List[str]


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def build_context_from_processed_docs(
    docs: List[ProcessedDoc],
    max_context_chars: Optional[int] = None,
) -> Tuple[str, bool]:
    context_parts: List[str] = []
    was_truncated = False
    current_length = 0

    for item in docs:
        header = f"[{item.doc_id}] Title: {item.title}\nSource: {item.source}\nExcerpt: "
        text = item.text
        separator_length = 2 if context_parts else 0

        if max_context_chars is not None:
            remaining = max_context_chars - current_length - len(header) - separator_length
            if remaining <= 40:
                was_truncated = True
                break
            if len(text) > remaining:
                text = text[:remaining].rstrip()
                was_truncated = True

        block = f"{header}{text}"
        context_parts.append(block)
        current_length += len(block) + separator_length

    return "\n\n".join(context_parts).strip(), was_truncated


def coerce_docs_to_processed_docs(docs: List[Any], max_doc_chars: int) -> List[ProcessedDoc]:
    processed: List[ProcessedDoc] = []
    for idx, doc in enumerate(docs, start=1):
        raw_text = getattr(doc, "page_content", "") or ""
        text = normalize_text(raw_text)
        if not text:
            continue
        if len(text) > max_doc_chars:
            text = text[:max_doc_chars].rstrip()

        metadata = dict(getattr(doc, "metadata", {}) or {})
        metadata["source"] = metadata_source(metadata)
        processed.append(
            ProcessedDoc(
                doc_id=f"DOC_{idx}",
                title=extract_doc_title(raw_text),
                source=metadata["source"],
                text=text,
                metadata=metadata,
            )
        )
    return processed


def apply_rule_postprocessing(
    docs: List[Any],
    max_doc_chars: int,
    dedup_threshold: float,
    max_docs: int,
) -> PostprocessDocsOutput:
    processed: List[ProcessedDoc] = []
    notes: List[str] = []

    for idx, doc in enumerate(docs, start=1):
        if len(processed) >= max_docs:
            notes.append(f"Limited context to {max_docs} post-processed chunks.")
            break

        raw_text = getattr(doc, "page_content", "") or ""
        text = normalize_text(raw_text)
        if not text:
            continue

        if len(text) > max_doc_chars:
            text = text[:max_doc_chars].rstrip()

        duplicate = False
        for existing in processed:
            if _similarity(existing.text, text) >= dedup_threshold:
                duplicate = True
                break
        if duplicate:
            continue

        metadata = dict(getattr(doc, "metadata", {}) or {})
        metadata["source"] = metadata_source(metadata)
        processed.append(
            ProcessedDoc(
                doc_id=f"DOC_{idx}",
                title=extract_doc_title(raw_text),
                source=metadata["source"],
                text=text,
                metadata=metadata,
            )
        )

    if len(processed) < len(docs):
        notes.append(f"Deduplicated/reduced evidence chunks from {len(docs)} to {len(processed)}.")

    context, _ = build_context_from_processed_docs(processed)

    return PostprocessDocsOutput(docs=processed, context=context, notes=notes)


def _deterministic_answer_cleanup(answer: str) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", (answer or "").strip())
    return cleaned


def maybe_refine_answer(
    answer: str,
    question: str,
    context: str,
    mode: str,
    refine_model: str,
) -> Tuple[str, Optional[str], bool]:
    cleaned = _deterministic_answer_cleanup(answer)
    if mode != "rules_plus_llm" or not cleaned:
        return cleaned, None, False

    system_prompt = (
        "Rewrite for clarity and structure only. Do not add new claims, facts, sources, or numbers. "
        "Keep fidelity to the supplied draft and context. Preserve every [DOC_n] citation exactly."
    )
    user_prompt = (
        f"Question:\n{question}\n\nContext:\n{context}\n\nDraft Answer:\n{cleaned}\n\n"
        "Return only the improved answer with citations preserved."
    )
    try:
        refined = run_refinement(
            model_name=refine_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        final_text = _deterministic_answer_cleanup(refined) or cleaned
        return final_text, None, True
    except Exception as exc:
        warning = f"Post-processing LLM refinement failed: {exc}"
        return cleaned, warning, False
