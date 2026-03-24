import unittest

from components.conversation import build_generation_question, build_retrieval_query, looks_like_follow_up


class TestConversationHelpers(unittest.TestCase):
    def test_follow_up_detection(self):
        self.assertTrue(looks_like_follow_up("How about London?"))
        self.assertFalse(looks_like_follow_up("What building retrofit policies are most common in Paris?"))

    def test_retrieval_query_includes_prior_user_turns_for_follow_up(self):
        query = build_retrieval_query(
            question="How about London?",
            messages=[
                {"role": "user", "content": "What building retrofit policies are most common in Paris?"},
                {"role": "assistant", "content": "Paris focuses on retrofit standards. [DOC_1]"},
            ],
            max_turns=4,
        )
        self.assertIn("How about London?", query)
        self.assertIn("Paris", query)

    def test_generation_question_embeds_recent_history(self):
        question = build_generation_question(
            question="Compare that with London.",
            messages=[
                {"role": "user", "content": "What building retrofit policies are most common in Paris?"},
                {"role": "assistant", "content": "Paris focuses on retrofit standards. [DOC_1]"},
            ],
            max_turns=4,
        )
        self.assertIn("Recent conversation", question)
        self.assertIn("Current question", question)


if __name__ == "__main__":
    unittest.main()
