import hashlib
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from components.generator import create_context_from_docs, generate_answer
from components.postprocessor import apply_rule_postprocessing, maybe_refine_answer
from components.rag_config import RagRuntimeConfig
from components.reranker import NoopReranker, build_reranker


def _safe_ms(seconds: float) -> float:
    return round(max(0.0, seconds) * 1000.0, 2)


def _source_from_metadata(metadata: Dict[str, Any]) -> str:
    return (
        metadata.get("source")
        or metadata.get("url")
        or metadata.get("file_path")
        or "https://www.c40knowledgehub.org/"
    )


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
) -> Dict[str, Any]:
    run_id = uuid4().hex
    warnings: List[str] = []
    error_type: Optional[str] = None
    refinement_applied = False

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
        base_search_kwargs = dict(getattr(retriever, "search_kwargs", {}) or {})
        base_fetch_k = int(base_search_kwargs.get("fetch_k", 20))
        candidate_k = max(int(retrieval_k), int(retrieval_k) * int(config.rerank_candidates_multiplier))
        base_search_kwargs["k"] = candidate_k
        base_search_kwargs["fetch_k"] = max(base_fetch_k, candidate_k)

        query_retriever = retriever.vectorstore.as_retriever(
            search_type=getattr(retriever, "search_type", "mmr"),
            search_kwargs=base_search_kwargs,
        )
        retrieved_docs = query_retriever.invoke(query)
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

        processed_docs_output = None
        if mode == "none":
            selected_docs = selected_docs[: int(retrieval_k)]
            context = create_context_from_docs(selected_docs)
            for idx, doc in enumerate(selected_docs, start=1):
                metadata = dict(getattr(doc, "metadata", {}) or {})
                source = _source_from_metadata(metadata)
                evidence_docs.append({"source": f"Doc {idx}: {source}", "text": getattr(doc, "page_content", "")[:900]})
        else:
            processed_docs_output = apply_rule_postprocessing(
                docs=selected_docs,
                max_doc_chars=config.postprocess_max_doc_chars,
                dedup_threshold=config.postprocess_dedup_threshold,
                max_docs=config.postprocess_max_docs,
            )
            warnings.extend(processed_docs_output.notes)
            context = processed_docs_output.context
            for idx, item in enumerate(processed_docs_output.docs, start=1):
                evidence_docs.append(
                    {
                        "source": f"Doc {idx}: {item.source}",
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
            answer = answer_fn(context, query, generation_model)
            if mode in {"rules_only", "rules_plus_llm"}:
                answer, refine_warning, refinement_applied = maybe_refine_answer(
                    answer=answer,
                    question=query,
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
