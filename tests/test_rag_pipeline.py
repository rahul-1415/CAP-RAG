import unittest

from components.rag_config import RagRuntimeConfig
from components.rag_pipeline import run_pipeline


class DummyDoc:
    def __init__(self, text, metadata=None):
        self.page_content = text
        self.metadata = metadata or {}


class FakeQueryRetriever:
    def __init__(self, docs):
        self._docs = docs

    def invoke(self, prompt):
        _ = prompt
        return list(self._docs)


class FakeVectorStore:
    def __init__(self, docs):
        self._docs = docs

    def as_retriever(self, search_type=None, search_kwargs=None):
        _ = search_type
        _ = search_kwargs
        return FakeQueryRetriever(self._docs)


class FakeRetriever:
    def __init__(self, docs):
        self.search_type = "mmr"
        self.search_kwargs = {"k": 5, "fetch_k": 20}
        self.vectorstore = FakeVectorStore(docs)


class TrackingRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None
        self.last_retrieval_k = None
        self.last_rerank_enabled = None
        self.last_candidate_multiplier = None

    def retrieve(self, query, retrieval_k, rerank_enabled, candidate_multiplier):
        self.last_query = query
        self.last_retrieval_k = retrieval_k
        self.last_rerank_enabled = rerank_enabled
        self.last_candidate_multiplier = candidate_multiplier
        return list(self.docs)


class TestRagPipeline(unittest.TestCase):
    def test_pipeline_runs_with_rerank_off(self):
        docs = [
            DummyDoc("Policy text 1", {"source": "https://www.c40knowledgehub.org/doc1"}),
            DummyDoc("Policy text 2", {"source": "https://www.c40knowledgehub.org/doc2"}),
        ]
        retriever = FakeRetriever(docs)
        config = RagRuntimeConfig(
            rerank_provider="cohere",
            cohere_rerank_model="rerank-v3.5",
            rerank_candidates_multiplier=4,
            postprocess_mode_default="rules_only",
            enable_analytics=False,
            analytics_db_path="analytics/rag_metrics.sqlite3",
            analytics_retention_days=30,
            analytics_retention_rows=50000,
            postprocess_dedup_threshold=0.92,
            postprocess_max_doc_chars=500,
            postprocess_max_docs=20,
        )

        result = run_pipeline(
            query="How can cities improve transit policy?",
            generation_model="llama-3.1-8b-instant",
            retrieval_k=2,
            rerank_enabled=False,
            postprocess_mode="rules_only",
            postprocess_model="llama-3.1-8b-instant",
            retriever=retriever,
            config=config,
            analytics_store=None,
            answer_fn=lambda context, question, model: f"Answer from {model} with {len(context)} chars for {question}",
        )
        self.assertTrue(result["success"])
        self.assertIn("Answer from", result["answer"])
        self.assertGreaterEqual(len(result["evidence_docs"]), 1)
        self.assertEqual(result["rerank"]["provider"], "cohere")
        self.assertIn("disabled", " ".join(result["warnings"]).lower())

    def test_pipeline_uses_conversation_history_and_context_cap(self):
        docs = [
            DummyDoc(
                "Title: Paris retrofit policy Content: " + ("Paris supports public retrofits. " * 30),
                {},
            ),
            DummyDoc(
                "Title: London retrofit policy Content: " + ("London requires retrofit roadmaps. " * 30),
                {},
            ),
        ]
        retriever = TrackingRetriever(docs)
        config = RagRuntimeConfig(
            rerank_provider="cohere",
            cohere_rerank_model="rerank-v3.5",
            rerank_candidates_multiplier=4,
            postprocess_mode_default="rules_only",
            enable_analytics=False,
            analytics_db_path="analytics/rag_metrics.sqlite3",
            analytics_retention_days=30,
            analytics_retention_rows=50000,
            postprocess_dedup_threshold=0.99,
            postprocess_max_doc_chars=400,
            postprocess_max_docs=20,
            max_context_chars=260,
            conversation_history_turns=4,
        )

        result = run_pipeline(
            query="How about London?",
            generation_model="llama-3.1-8b-instant",
            retrieval_k=2,
            rerank_enabled=False,
            postprocess_mode="rules_only",
            postprocess_model="llama-3.1-8b-instant",
            retriever=retriever,
            config=config,
            analytics_store=None,
            conversation_messages=[
                {"role": "user", "content": "What retrofit policies are used in Paris?"},
                {"role": "assistant", "content": "Paris uses retrofit roadmaps and standards. [DOC_1]"},
            ],
            answer_fn=lambda context, question, model: f"{model} :: {len(context)} :: {question}",
        )

        self.assertTrue(result["success"])
        self.assertIn("Paris", retriever.last_query)
        self.assertIn("Recent conversation", result["answer"])
        self.assertTrue(any("trimmed" in warning.lower() for warning in result["warnings"]))
        self.assertEqual(result["evidence_docs"][0]["doc_id"], "DOC_1")
        self.assertIn("title", result["evidence_docs"][0])


if __name__ == "__main__":
    unittest.main()
