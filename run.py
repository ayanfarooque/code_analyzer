import os
import requests

api_key = os.environ.get("GOOGLE_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/models"
params = {"key": api_key}
response = requests.get(url, params=params)
print(response.json())