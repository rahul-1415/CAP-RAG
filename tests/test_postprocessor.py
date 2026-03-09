import unittest

from components.postprocessor import SOURCE_FALLBACK, apply_rule_postprocessing, maybe_refine_answer


class DummyDoc:
    def __init__(self, text, metadata=None):
        self.page_content = text
        self.metadata = metadata or {}


class TestPostprocessor(unittest.TestCase):
    def test_rule_postprocessing_dedups_and_preserves_source_fallback(self):
        docs = [
            DummyDoc("Cities should expand bus electrification rapidly.", {"source": "https://example.com/a"}),
            DummyDoc("Cities should expand bus electrification rapidly. ", {}),
            DummyDoc("Cooling centers reduce heatwave risk in vulnerable neighborhoods.", {}),
        ]
        result = apply_rule_postprocessing(docs, max_doc_chars=200, dedup_threshold=0.9, max_docs=10)
        self.assertEqual(len(result.docs), 2)
        self.assertTrue(result.context.startswith("[DOC_1]"))
        self.assertEqual(result.docs[1].source, SOURCE_FALLBACK)

    def test_refine_answer_none_mode_keeps_deterministic_cleanup_only(self):
        answer, warning, refined = maybe_refine_answer(
            answer="Line 1\n\n\nLine 2",
            question="Q",
            context="C",
            mode="none",
            refine_model="llama-3.1-8b-instant",
        )
        self.assertEqual(answer, "Line 1\n\nLine 2")
        self.assertIsNone(warning)
        self.assertFalse(refined)


if __name__ == "__main__":
    unittest.main()
