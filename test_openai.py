"""
Minimal check to list models using Groq's OpenAI-compatible endpoint.
Requires GROQ_API_KEY; optionally uses GROQ_API_BASE_URL (defaults to https://api.groq.com/openai/v1).
"""

import os
from openai import OpenAI


api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is not set.")

base_url = os.getenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")

client = OpenAI(api_key=api_key, base_url=base_url)
print(client.models.list())
