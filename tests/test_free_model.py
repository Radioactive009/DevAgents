import os
import time
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("OPENROUTER_API_KEY")

models_to_test = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

for model in models_to_test:
    print(f"\nTesting model: {model}")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Write a 1-line python function to add two numbers."}],
        "max_tokens": 50
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("SUCCESS! Output:")
            print(data['choices'][0]['message']['content'])
            break # Stop at first working model
    except Exception as e:
        print(f"FAILED: {e}")
