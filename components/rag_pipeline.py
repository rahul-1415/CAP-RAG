import hashlib
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from components.conversation import build_generation_question, build_retrieval_query
from components.generator import generate_answer
from components.postprocessor import (
    apply_rule_postprocessing,
    build_context_from_processed_docs,
    coerce_docs_to_processed_docs,
    maybe_refine_answer,
)
from components.rag_config import RagRuntimeConfig
from components.reranker import NoopReranker, build_reranker


def _safe_ms(seconds: float) -> float:
    return round(max(0.0, seconds) * 1000.0, 2)

def run_pipeline(
    query: str,
    generation_model: str,
    retrieval_k: int,
    rerank_enabled: bool,
    postprocess_mode: str,
    postprocess_model: str,
    retriever: Any,
    config: RagRuntimeConfig,
    analytics_store: Any = None,
    answer_fn: Callable[[str, str, str], str] = generate_answer,
    conversation_messages: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    run_id = uuid4().hex
    warnings: List[str] = []
    error_type: Optional[str] = None
    refinement_applied = False
    conversation_messages = list(conversation_messages or [])

    retrieval_ms = 0.0
    rerank_ms = 0.0
    generation_ms = 0.0
    postprocess_ms = 0.0

    final_answer = ""
    context = ""
    retrieved_docs: List[Any] = []
    selected_docs: List[Any] = []
    evidence_docs: List[Dict[str, str]] = []
    rerank_records = []
    rerank_provider = "none"
    rerank_model = "none"
    rerank_fallback_reason = None

    pipeline_start = time.perf_counter()

    try:
        retrieval_start = time.perf_counter()
        retrieval_query = build_retrieval_query(
            question=query,
            messages=conversation_messages,
            max_turns=config.conversation_history_turns,
        )
        generation_question = build_generation_question(
            question=query,
            messages=conversation_messages,
            max_turns=config.conversation_history_turns,
        )
        if retrieval_query.strip() != (query or "").strip():
            warnings.append("Resolved the latest question using recent chat context.")

        if hasattr(retriever, "retrieve"):
            retrieved_docs = retriever.retrieve(
                query=retrieval_query,
                retrieval_k=int(retrieval_k),
                rerank_enabled=bool(rerank_enabled),
                candidate_multiplier=int(config.rerank_candidates_multiplier),
            )
        else:
            base_search_kwargs = dict(getattr(retriever, "search_kwargs", {}) or {})
            base_fetch_k = int(base_search_kwargs.get("fetch_k", 20))
            candidate_k = int(retrieval_k)
            if rerank_enabled:
                candidate_k = max(int(retrieval_k), int(retrieval_k) * int(config.rerank_candidates_multiplier))
            base_search_kwargs["k"] = candidate_k
            base_search_kwargs["fetch_k"] = max(base_fetch_k, candidate_k)
            query_retriever = retriever.vectorstore.as_retriever(
                search_type=getattr(retriever, "search_type", "mmr"),
                search_kwargs=base_search_kwargs,
            )
            retrieved_docs = query_retriever.invoke(retrieval_query)
        retrieval_ms = _safe_ms(time.perf_counter() - retrieval_start)

        rerank_start = time.perf_counter()
        if rerank_enabled and retrieved_docs:
            reranker = build_reranker(
                provider=config.rerank_provider,
                api_key=os.getenv("COHERE_API_KEY"),
                model=config.cohere_rerank_model,
            )
        else:
            reason = None
            if not rerank_enabled:
                reason = "Reranking disabled by user."
            reranker = NoopReranker(
                provider=config.rerank_provider,
                model=config.cohere_rerank_model,
                fallback_reason=reason,
            )

        try:
            rerank_output = reranker.rerank(query=query, docs=retrieved_docs, top_k=int(retrieval_k))
        except Exception as rerank_exc:
            rerank_output = NoopReranker(
                provider=config.rerank_provider,
                model=config.cohere_rerank_model,
                fallback_reason=f"Reranking failed ({rerank_exc}). Falling back to base retrieval order.",
            ).rerank(query=query, docs=retrieved_docs, top_k=int(retrieval_k))

        rerank_ms = _safe_ms(time.perf_counter() - rerank_start)
        rerank_provider = rerank_output.provider
        rerank_model = rerank_output.model
        rerank_fallback_reason = rerank_output.fallback_reason
        if rerank_fallback_reason:
            warnings.append(rerank_fallback_reason)

        rerank_records = rerank_output.records
        selected_docs = rerank_output.docs[: int(retrieval_k)]

        postprocess_start = time.perf_counter()
        mode = (postprocess_mode or "rules_only").strip().lower()
        if mode not in {"none", "rules_only", "rules_plus_llm"}:
            mode = "rules_only"

        if mode == "none":
            processed_docs = coerce_docs_to_processed_docs(
                docs=selected_docs[: int(retrieval_k)],
                max_doc_chars=config.postprocess_max_doc_chars,
            )
        else:
            processed_docs_output = apply_rule_postprocessing(
                docs=selected_docs,
                max_doc_chars=config.postprocess_max_doc_chars,
                dedup_threshold=config.postprocess_dedup_threshold,
                max_docs=config.postprocess_max_docs,
            )
            warnings.extend(processed_docs_output.notes)
            processed_docs = processed_docs_output.docs

        context, was_context_trimmed = build_context_from_processed_docs(
            processed_docs,
            max_context_chars=config.max_context_chars,
        )
        if was_context_trimmed:
            warnings.append(f"Context was trimmed to {config.max_context_chars} characters before generation.")

        for item in processed_docs:
            evidence_docs.append(
                {
                    "doc_id": item.doc_id,
                    "title": item.title,
                    "source": item.source,
                    "text": item.text[:900],
                }
            )
        postprocess_ms = _safe_ms(time.perf_counter() - postprocess_start)

        generation_start = time.perf_counter()
        if not context.strip():
            final_answer = (
                "I could not find relevant policy context for that query. "
                "Try adding more specific details (policy name, region, or year)."
            )
        else:
            answer = answer_fn(context, generation_question, generation_model)
            if mode in {"rules_only", "rules_plus_llm"}:
                answer, refine_warning, refinement_applied = maybe_refine_answer(
                    answer=answer,
                    question=generation_question,
                    context=context,
                    mode=mode,
                    refine_model=postprocess_model or generation_model,
                )
                if refine_warning:
                    warnings.append(refine_warning)
            final_answer = answer
        generation_ms = _safe_ms(time.perf_counter() - generation_start)
    except Exception as exc:
        error_type = "pipeline_error"
        final_answer = f"Retriever failed: {exc}"

    total_ms = _safe_ms(time.perf_counter() - pipeline_start)
    success = error_type is None

    run_payload = {
        "run_id": run_id,
        "ts": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "query_hash": hashlib.sha256((query or "").encode("utf-8")).hexdigest(),
        "generation_model": generation_model,
        "postprocess_model": postprocess_model,
        "rerank_provider": rerank_provider,
        "rerank_model": rerank_model,
        "retrieval_k": int(retrieval_k),
        "rerank_enabled": bool(rerank_enabled),
        "postprocess_mode": postprocess_mode,
        "success": success,
        "error_type": error_type,
        "warning_text": " | ".join(warnings) if warnings else None,
        "total_ms": total_ms,
        "retrieval_ms": retrieval_ms,
        "rerank_ms": rerank_ms,
        "generation_ms": generation_ms,
        "postprocess_ms": postprocess_ms,
        "context_chars": len(context or ""),
        "response_chars": len(final_answer or ""),
        "retrieved_docs": len(retrieved_docs),
        "selected_docs": len(selected_docs),
        "rerank_fallback_reason": rerank_fallback_reason,
        "refinement_applied": refinement_applied,
    }

    doc_payloads = [
        {
            "rank_before": row.rank_before,
            "rank_after": row.rank_after,
            "source": row.source,
            "score_raw": row.score_raw,
            "score_rerank": row.score_rerank,
            "selected": row.selected,
        }
        for row in rerank_records
    ]
    if analytics_store is not None:
        try:
            analytics_store.log_run(run_payload, doc_payloads)
        except Exception:
            pass

    return {
        "run_id": run_id,
        "success": success,
        "error_type": error_type,
        "answer": final_answer,
        "evidence_docs": evidence_docs,
        "retrieved_docs_count": len(retrieved_docs),
        "selected_docs_count": len(selected_docs),
        "warnings": warnings,
        "timings": {
            "total_ms": total_ms,
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
            "generation_ms": generation_ms,
            "postprocess_ms": postprocess_ms,
        },
        "rerank": {
            "provider": rerank_provider,
            "model": rerank_model,
            "fallback_reason": rerank_fallback_reason,
        },
        "context_chars": len(context or ""),
    }
