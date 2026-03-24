import tempfile
import unittest
from pathlib import Path

from components.analytics_store import AnalyticsStore


class TestAnalyticsStore(unittest.TestCase):
    def test_log_and_read_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "metrics.sqlite3"
            store = AnalyticsStore(db_path=db_path, enabled=True)

            run_payload = {
                "run_id": "run_1",
                "ts": "2099-01-01 00:00:00",
                "query_hash": "abc123",
                "generation_model": "llama-3.1-8b-instant",
                "postprocess_model": "llama-3.1-8b-instant",
                "rerank_provider": "cohere",
                "rerank_model": "rerank-v3.5",
                "retrieval_k": 5,
                "rerank_enabled": True,
                "postprocess_mode": "rules_only",
                "success": True,
                "error_type": None,
                "warning_text": None,
                "total_ms": 123.4,
                "retrieval_ms": 12.0,
                "rerank_ms": 21.0,
                "generation_ms": 80.0,
                "postprocess_ms": 10.0,
                "context_chars": 2200,
                "response_chars": 540,
                "retrieved_docs": 15,
                "selected_docs": 5,
                "rerank_fallback_reason": None,
                "refinement_applied": False,
            }
            doc_payloads = [
                {
                    "rank_before": 1,
                    "rank_after": 1,
                    "source": "https://www.c40knowledgehub.org/",
                    "score_raw": 1.0,
                    "score_rerank": 0.95,
                    "selected": True,
                }
            ]
            store.log_run(run_payload, doc_payloads)

            runs = store.read_query_runs(days=36500)
            self.assertEqual(len(runs), 1)

            docs = store.read_doc_rows(["run_1"])
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs.iloc[0]["run_id"], "run_1")

            store.log_feedback(run_id="run_1", feedback_type="helpful")
            store.log_source_click(
                run_id="run_1",
                doc_id="DOC_1",
                source="https://www.c40knowledgehub.org/",
                title="C40 Knowledge Hub document",
                position=1,
            )

            feedback_rows = store.read_feedback_rows(["run_1"])
            self.assertEqual(len(feedback_rows), 1)
            self.assertEqual(feedback_rows.iloc[0]["feedback_type"], "helpful")

            source_click_rows = store.read_source_click_rows(["run_1"])
            self.assertEqual(len(source_click_rows), 1)
            self.assertEqual(source_click_rows.iloc[0]["doc_id"], "DOC_1")


if __name__ == "__main__":
    unittest.main()
