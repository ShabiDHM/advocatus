# Phoenix Protocol: OpenRouter Embedding Diagnostic
import os
import requests
from dotenv import load_dotenv

def test_api():
    load_dotenv("backend/.env")
    key = os.getenv("OPENROUTER_API_KEY")
    
    if not key:
        print("ERROR: OPENROUTER_API_KEY is missing from your .env file!")
        return
        
    print(f"Testing OpenRouter Key (Starts with: {key[:10]}...)")
    
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/text-embedding-3-small",
        "input": ["Integriteti i sistemit."]
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"HTTP Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            vector = data.get("data", [{}])[0].get("embedding", [])
            print(f"SUCCESS: Vector received! Dimensions: {len(vector)}")
        else:
            print(f"FAILED: {r.text}")
    except Exception as e:
        print(f"Network Error: {e}")

if __name__ == "__main__":
    test_api()