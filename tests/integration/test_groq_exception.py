import os
import groq

api_key = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=5
    )
    print("SUCCESS")
except Exception as e:
    msg = str(e)
    # Mask key if present
    if api_key in msg:
        msg = msg.replace(api_key, "********")
    print(f"EXCEPTION TYPE: {type(e)}")
    print(f"EXCEPTION MSG: {msg}")
