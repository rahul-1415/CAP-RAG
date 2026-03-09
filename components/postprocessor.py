import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from components.generator import run_refinement


SOURCE_FALLBACK = "https://www.c40knowledgehub.org/"


@dataclass
class ProcessedDoc:
    doc_id: str
    source: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class PostprocessDocsOutput:
    docs: List[ProcessedDoc]
    context: str
    notes: List[str]


def _normalize_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    compact = compact.replace(" .", ".")
    return compact


def _doc_source(metadata: Dict[str, Any]) -> str:
    return (
        metadata.get("source")
        or metadata.get("url")
        or metadata.get("file_path")
        or SOURCE_FALLBACK
    )


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


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

        text = _normalize_text(getattr(doc, "page_content", ""))
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
        metadata["source"] = _doc_source(metadata)
        processed.append(
            ProcessedDoc(
                doc_id=f"DOC_{idx}",
                source=metadata["source"],
                text=text,
                metadata=metadata,
            )
        )

    if len(processed) < len(docs):
        notes.append(f"Deduplicated/reduced evidence chunks from {len(docs)} to {len(processed)}.")

    context_parts = []
    for item in processed:
        context_parts.append(f"[{item.doc_id}] Source: {item.source}\n{item.text}")
    context = "\n\n".join(context_parts).strip()

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
        "Keep fidelity to the supplied draft and context."
    )
    user_prompt = (
        f"Question:\n{question}\n\nContext:\n{context}\n\nDraft Answer:\n{cleaned}\n\n"
        "Return only the improved answer."
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
