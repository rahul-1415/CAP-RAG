import os
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from components.document_utils import document_key

CHROMA_IMPORT_ERROR: Optional[Exception] = None

try:
    import chromadb
    from langchain_chroma import Chroma
except Exception as exc:  # pragma: no cover - exercised in deployment resolution failures.
    chromadb = None  # type: ignore[assignment]
    Chroma = Any  # type: ignore[assignment,misc]
    CHROMA_IMPORT_ERROR = exc

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "Chroma" / "env_policy"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
COLLECTION_NAME = "env_policy_bge"
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'/-]{1,}")


@dataclass(frozen=True)
class CollectionStats:
    collection_name: str
    document_count: int


class LexicalIndex:
    def __init__(self, docs: Sequence[Document]):
        self.docs = list(docs)
        self._postings: Dict[str, Dict[int, int]] = defaultdict(dict)
        self._doc_lengths: List[int] = []
        self._title_tokens: List[set] = []
        self._normalized_texts: List[str] = []
        self._avg_doc_len = 0.0
        self._doc_count = len(self.docs)

        total_tokens = 0
        for idx, doc in enumerate(self.docs):
            text = getattr(doc, "page_content", "") or ""
            title, _, _ = text.partition("Content:")
            title_tokens = set(self._tokenize(title))
            tokens = self._tokenize(text)
            token_counts = Counter(tokens)
            for token, freq in token_counts.items():
                self._postings[token][idx] = freq
            doc_len = len(tokens)
            self._doc_lengths.append(doc_len)
            self._title_tokens.append(title_tokens)
            self._normalized_texts.append(text.lower())
            total_tokens += doc_len

        self._avg_doc_len = float(total_tokens) / float(max(self._doc_count, 1))

    def _tokenize(self, text: str) -> List[str]:
        return [token.lower() for token in TOKEN_RE.findall(text or "")]

    def _idf(self, token: str) -> float:
        doc_freq = len(self._postings.get(token, {}))
        if doc_freq == 0:
            return 0.0
        return math.log(1.0 + (self._doc_count - doc_freq + 0.5) / (doc_freq + 0.5))

    def search(self, query: str, top_k: int) -> List[Document]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.docs:
            return []

        scores: Dict[int, float] = defaultdict(float)
        k1 = 1.5
        b = 0.75
        normalized_query = " ".join(query_tokens)

        for token in query_tokens:
            idf = self._idf(token)
            for doc_idx, term_freq in self._postings.get(token, {}).items():
                doc_len = self._doc_lengths[doc_idx]
                denominator = term_freq + k1 * (1.0 - b + b * (float(doc_len) / float(max(self._avg_doc_len, 1.0))))
                score = idf * ((term_freq * (k1 + 1.0)) / max(denominator, 1e-9))
                scores[doc_idx] += score

        if len(query_tokens) >= 2:
            for doc_idx, text in enumerate(self._normalized_texts):
                if normalized_query in text:
                    scores[doc_idx] += 2.5

        query_token_set = set(query_tokens)
        for doc_idx, title_tokens in enumerate(self._title_tokens):
            overlap = len(query_token_set & title_tokens)
            if overlap:
                scores[doc_idx] += 0.4 * overlap

        ranked_doc_indexes = [
            doc_idx
            for doc_idx, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if score > 0
        ]
        return [self.docs[doc_idx] for doc_idx in ranked_doc_indexes[:top_k]]


class ClimatePolicyRetriever:
    def __init__(self, vectorstore: Chroma, search_type: str, search_kwargs: Dict[str, int], lexical_index: LexicalIndex):
        self.vectorstore = vectorstore
        self.search_type = search_type
        self.search_kwargs = dict(search_kwargs)
        self.lexical_index = lexical_index

    def _dense_retrieve(self, query: str, limit: int) -> List[Document]:
        search_kwargs = dict(self.search_kwargs)
        fetch_k = int(search_kwargs.get("fetch_k", max(limit, 20)))
        search_kwargs["k"] = int(limit)
        search_kwargs["fetch_k"] = max(fetch_k, int(limit))
        query_retriever = self.vectorstore.as_retriever(
            search_type=self.search_type,
            search_kwargs=search_kwargs,
        )
        return list(query_retriever.invoke(query))

    def retrieve(self, query: str, retrieval_k: int, rerank_enabled: bool, candidate_multiplier: int) -> List[Document]:
        limit = max(int(retrieval_k), 1)
        candidate_k = limit if not rerank_enabled else max(limit, limit * int(candidate_multiplier))

        dense_docs = self._dense_retrieve(query=query, limit=candidate_k)
        lexical_docs = self.lexical_index.search(query=query, top_k=candidate_k)
        return _fuse_ranked_lists([dense_docs, lexical_docs], limit=candidate_k)


def _fuse_ranked_lists(ranked_lists: Iterable[Sequence[Document]], limit: int) -> List[Document]:
    scores: Dict[str, float] = defaultdict(float)
    doc_lookup: Dict[str, Document] = {}

    for ranked_docs in ranked_lists:
        for rank, doc in enumerate(ranked_docs, start=1):
            key = document_key(doc)
            doc_lookup[key] = doc
            scores[key] += 1.0 / float(rank + 60)

    ordered_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [doc_lookup[key] for key in ordered_keys[:limit]]


def _require_chroma_dependencies() -> None:
    if CHROMA_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "Chroma dependencies failed to import. This deployment likely resolved incompatible "
        "`chromadb` or `protobuf` packages. Rebuild with the pinned versions from requirements.txt."
    ) from CHROMA_IMPORT_ERROR


def _build_client_settings():
    _require_chroma_dependencies()
    return chromadb.config.Settings(
        is_persistent=True,
        persist_directory=str(DB_DIR),
        anonymized_telemetry=False,
    )


@lru_cache(maxsize=1)
def _get_chroma_client():
    return chromadb.Client(settings=_build_client_settings())


@lru_cache(maxsize=1)
def get_collection_stats() -> CollectionStats:
    _require_chroma_dependencies()
    if not DB_DIR.exists():
        return CollectionStats(collection_name=COLLECTION_NAME, document_count=0)

    client = _get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)
    return CollectionStats(collection_name=COLLECTION_NAME, document_count=collection.count())


def _load_collection_documents() -> List[Document]:
    _require_chroma_dependencies()
    client = _get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)
    payload = collection.get(include=["documents", "metadatas"])

    docs: List[Document] = []
    for idx, raw_text in enumerate(payload.get("documents") or []):
        metadata = dict(((payload.get("metadatas") or [None])[idx]) or {})
        if payload.get("ids"):
            metadata["_doc_key"] = str(payload["ids"][idx])
        docs.append(Document(page_content=raw_text or "", metadata=metadata))
    return docs


def initialize_retriever():
    _require_chroma_dependencies()
    if not DB_DIR.exists():
        raise FileNotFoundError(
            f"Chroma DB directory not found at {DB_DIR}. Ensure the vector DB is available in deployment."
        )

    # Normalized vectors generally improve cosine similarity retrieval stability.
    embedder = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

    bge_vectorstore = Chroma(
        embedding_function=embedder,
        client=_get_chroma_client(),
        collection_name=COLLECTION_NAME,
        collection_metadata={"hnsw:space": "cosine"},
    )

    lexical_index = LexicalIndex(_load_collection_documents())
    return ClimatePolicyRetriever(
        vectorstore=bge_vectorstore,
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5},
        lexical_index=lexical_index,
    )
