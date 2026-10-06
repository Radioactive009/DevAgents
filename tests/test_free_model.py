import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("OPENROUTER_API_KEY")

model = "cohere/north-mini-code:free"
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
        resp_data = json.loads(response.read().decode('utf-8'))
        print("SUCCESS! Output:")
        print(resp_data['choices'][0]['message']['content'])
except Exception as e:
    print(f"FAILED: {e}")
