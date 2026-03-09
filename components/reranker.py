from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RerankDocRecord:
    index: int
    source: str
    rank_before: int
    rank_after: Optional[int]
    score_raw: Optional[float]
    score_rerank: Optional[float]
    selected: bool


@dataclass
class RerankOutput:
    docs: List[Any]
    records: List[RerankDocRecord]
    provider: str
    model: str
    fallback_reason: Optional[str] = None


def _doc_source(doc: Any) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    return (
        metadata.get("source")
        or metadata.get("url")
        or metadata.get("file_path")
        or "https://www.c40knowledgehub.org/"
    )


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, docs: List[Any], top_k: int) -> RerankOutput:
        raise NotImplementedError


class NoopReranker(BaseReranker):
    def __init__(self, provider: str = "none", model: str = "none", fallback_reason: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.fallback_reason = fallback_reason

    def rerank(self, query: str, docs: List[Any], top_k: int) -> RerankOutput:
        limit = min(max(int(top_k), 1), len(docs))
        selected_docs = docs[:limit]
        total = max(len(docs), 1)
        records = []
        for idx, doc in enumerate(docs, start=1):
            selected = idx <= limit
            score_raw = float(total - idx + 1) / float(total)
            records.append(
                RerankDocRecord(
                    index=idx - 1,
                    source=_doc_source(doc),
                    rank_before=idx,
                    rank_after=idx if selected else None,
                    score_raw=score_raw,
                    score_rerank=score_raw if selected else None,
                    selected=selected,
                )
            )
        return RerankOutput(
            docs=selected_docs,
            records=records,
            provider=self.provider,
            model=self.model,
            fallback_reason=self.fallback_reason,
        )


class CohereReranker(BaseReranker):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.provider = "cohere"

    def _build_client(self):
        import cohere

        return cohere.Client(self.api_key)

    def _extract_results(self, response: Any) -> List[Any]:
        if response is None:
            return []
        if isinstance(response, dict):
            return response.get("results", []) or []
        results = getattr(response, "results", None)
        return list(results or [])

    def _extract_item_fields(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, dict):
            index = item.get("index")
            score = item.get("relevance_score")
            return {"index": index, "score": score}
        index = getattr(item, "index", None)
        score = getattr(item, "relevance_score", None)
        return {"index": index, "score": score}

    def rerank(self, query: str, docs: List[Any], top_k: int) -> RerankOutput:
        if not docs:
            return RerankOutput(
                docs=[],
                records=[],
                provider=self.provider,
                model=self.model,
                fallback_reason=None,
            )

        limit = min(max(int(top_k), 1), len(docs))
        records: List[RerankDocRecord] = []
        total = max(len(docs), 1)
        for idx, doc in enumerate(docs, start=1):
            records.append(
                RerankDocRecord(
                    index=idx - 1,
                    source=_doc_source(doc),
                    rank_before=idx,
                    rank_after=None,
                    score_raw=float(total - idx + 1) / float(total),
                    score_rerank=None,
                    selected=False,
                )
            )

        documents = [getattr(doc, "page_content", "") for doc in docs]

        client = self._build_client()
        response = client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=limit,
        )

        ranked_indices: List[int] = []
        for rank_after, item in enumerate(self._extract_results(response), start=1):
            fields = self._extract_item_fields(item)
            idx = fields.get("index")
            if idx is None:
                continue
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue
            if idx_int < 0 or idx_int >= len(docs) or idx_int in ranked_indices:
                continue
            ranked_indices.append(idx_int)
            score = fields.get("score")
            try:
                score_value = float(score) if score is not None else None
            except (TypeError, ValueError):
                score_value = None
            rec = records[idx_int]
            rec.rank_after = rank_after
            rec.score_rerank = score_value
            rec.selected = True

        if not ranked_indices:
            raise RuntimeError("Cohere returned no usable rerank results.")

        reranked_docs = [docs[i] for i in ranked_indices]
        return RerankOutput(
            docs=reranked_docs,
            records=records,
            provider=self.provider,
            model=self.model,
            fallback_reason=None,
        )


def build_reranker(provider: str, api_key: Optional[str], model: str) -> BaseReranker:
    normalized_provider = (provider or "none").strip().lower()
    if normalized_provider == "cohere":
        if not api_key:
            return NoopReranker(
                provider="cohere",
                model=model,
                fallback_reason="COHERE_API_KEY missing. Falling back to base retrieval order.",
            )
        try:
            return CohereReranker(api_key=api_key, model=model)
        except Exception as exc:
            return NoopReranker(
                provider="cohere",
                model=model,
                fallback_reason=f"Reranker unavailable ({exc}). Falling back to base retrieval order.",
            )

    return NoopReranker(
        provider=normalized_provider or "none",
        model=model,
        fallback_reason=f"Unsupported reranker provider '{provider}'. Falling back to base retrieval order.",
    )
