import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def classify_error(e: Exception) -> str:
    err_str = str(type(e)).lower() + " " + str(e).lower()
    if "auth" in err_str or "401" in err_str:
        return "AUTHENTICATION_ERROR"
    elif "rate" in err_str or "429" in err_str:
        return "RATE_LIMITED"
    elif "timeout" in err_str:
        return "TIMEOUT"
    elif "connection" in err_str:
        return "NETWORK_ERROR"
    else:
        return "PROVIDER_ERROR"

def test_groq_direct():
    # Use explicit override
    load_dotenv(override=True)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ DIRECT: FAIL - MISSING_API_KEY")
        return
        
    try:
        import groq
        client = groq.Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "user", "content": "Reply with exactly: OK"}
            ],
            max_tokens=5,
            temperature=0.1
        )
        
        # Checking if we get a valid response
        if response and response.choices and len(response.choices) > 0:
            print("GROQ DIRECT: PASS")
        else:
            print("GROQ DIRECT: FAIL - INVALID_RESPONSE")
            
    except Exception as e:
        print(f"GROQ DIRECT: FAIL - {classify_error(e)}")

if __name__ == "__main__":
    test_groq_direct()
