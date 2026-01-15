# Migrated from AI-modernization-tool/embedder.py
# Placeholder: implement BGEEmbedder class here based on original logic


import os
import requests
from dotenv import load_dotenv
load_dotenv()

class BGEEmbedder:
    def __init__(self, api_key=None):
        # Prefer GOOGLE_API_KEY from .env, fallback to GEMINI_API_KEY
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedText"

    def embed(self, text):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment or passed to BGEEmbedder.")
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        data = {"text": text}
        response = requests.post(self.api_url, headers=headers, params=params, json=data)
        if response.status_code == 200:
            result = response.json()
            # Gemini returns embeddings under 'embedding' key
            return result.get("embedding", [0.0] * 768)
        else:
            print(f"Gemini API error: {response.status_code} {response.text}")
            return [0.0] * 768
