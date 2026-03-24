import unittest

from streamlit.testing.v1 import AppTest


class TestStreamlitSmoke(unittest.TestCase):
    def test_app_starts_and_can_create_new_chat(self):
        app = AppTest.from_file("app.py", default_timeout=20)
        app.run(timeout=20)

        self.assertIn("Chats", [item.value for item in app.title])
        self.assertEqual(len(app.session_state["chats"]), 1)
        self.assertEqual(app.session_state["chats"][0]["title"], "My first chat")

        app.button[0].click().run(timeout=20)

        self.assertEqual(len(app.session_state["chats"]), 2)
        self.assertEqual(app.session_state["chats"][0]["title"], "My second chat")

    def test_settings_page_respects_theme_query_param_in_nav_links(self):
        settings = AppTest.from_file("pages/4_Settings.py", default_timeout=20)
        settings.query_params["theme"] = "dark"
        settings.run(timeout=20)

        self.assertTrue(settings.session_state["dark_mode"])
        markdown_values = [item.value for item in settings.markdown]
        self.assertTrue(any("/?theme=dark" in value for value in markdown_values))
        self.assertTrue(any("/Analytics?theme=dark" in value for value in markdown_values))


if __name__ == "__main__":
    unittest.main()
