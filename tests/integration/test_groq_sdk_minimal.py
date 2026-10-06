import os
from dotenv import load_dotenv
from groq import Groq
import httpx
import logging

load_dotenv(override=True)

logging.basicConfig(level=logging.DEBUG)

def test_minimal():
    # Use explicit base URL and debug transport if needed
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    print(f"Base URL: {client.base_url}")
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "user", "content": "Reply with exactly: GROQ SDK WORKS"}
            ],
            max_tokens=10
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"FAILED: {type(e)} {e}")

if __name__ == "__main__":
    test_minimal()
