# Migrated from AI-modernization-tool/chat.py
# Placeholder: implement ModernizationChat class here based on original logic


import os
import requests
from dotenv import load_dotenv
load_dotenv()

class ModernizationChat:
    def __init__(self, api_key=None):
        # Prefer GOOGLE_API_KEY from .env, fallback to GEMINI_API_KEY
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    def chat(self, query, context=None):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment or passed to ModernizationChat.")
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        prompt = query
        if context:
            prompt = f"Context: {context}\nQuestion: {query}"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(self.api_url, headers=headers, params=params, json=data)
        if response.status_code == 200:
            result = response.json()
            # Gemini returns text under 'candidates' -> 'content' -> 'parts'
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return str(result)
        else:
            print(f"Gemini API error: {response.status_code} {response.text}")
            return "[Gemini API error]"
