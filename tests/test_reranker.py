import unittest

from components.reranker import NoopReranker, build_reranker


class DummyDoc:
    def __init__(self, text, metadata=None):
        self.page_content = text
        self.metadata = metadata or {}


class TestReranker(unittest.TestCase):
    def test_missing_cohere_key_falls_back_to_noop(self):
        docs = [
            DummyDoc("Doc one", {"source": "https://www.c40knowledgehub.org/doc1"}),
            DummyDoc("Doc two", {"source": "https://www.c40knowledgehub.org/doc2"}),
        ]
        reranker = build_reranker(provider="cohere", api_key=None, model="rerank-v3.5")
        self.assertIsInstance(reranker, NoopReranker)

        output = reranker.rerank(query="test query", docs=docs, top_k=1)
        self.assertEqual(len(output.docs), 1)
        self.assertIsNotNone(output.fallback_reason)
        self.assertIn("COHERE_API_KEY", output.fallback_reason)
        self.assertEqual(output.records[0].rank_before, 1)
        self.assertTrue(output.records[0].selected)


if __name__ == "__main__":
    unittest.main()
