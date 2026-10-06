import os
import urllib.request
from dotenv import load_dotenv

def mask_key(key):
    if not key:
        return "None"
    if len(key) <= 8:
        return "****"
    return f"{key[:7]}...{key[-4:]}"

def test_auth():
    print(f"CWD: {os.getcwd()}")
    
    # Check for other .env files
    env_files = [f for f in os.listdir('.') if f.startswith('.env')]
    print(f"Found root .env files: {env_files}")
    if os.path.exists('configs'):
        config_envs = [f for f in os.listdir('configs') if f.startswith('.env')]
        print(f"Found configs/ .env files: {config_envs}")
    
    # Load default .env explicitly
    load_dotenv(override=True)
    
    key = os.environ.get("GROQ_API_KEY")
    masked = mask_key(key)
    print(f"Loaded GROQ_API_KEY: {masked}")
    
    if not key:
        print("Error: No key loaded.")
        return
        
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "groq-python/1.1.2"
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            print(f"Status Code: {status_code}")
            import json
            models = json.loads(body).get("data", [])
            print("Models available:")
            for m in models:
                print(f" - {m.get('id')}")
    except urllib.error.HTTPError as e:
        status_code = e.code
        body = e.read().decode('utf-8')
        print(f"Status Code: {status_code}")
        print(f"Response Body: {body}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    test_auth()
