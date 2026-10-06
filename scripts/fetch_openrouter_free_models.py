import urllib.request
import json

def fetch_free_models():
    url = "https://openrouter.ai/api/v1/models"
    req = urllib.request.Request(url)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = data.get('data', [])
            free_models = []
            
            for m in models:
                pricing = m.get('pricing', {})
                # Check if prompt and completion costs are 0
                prompt_cost = float(pricing.get('prompt', -1))
                completion_cost = float(pricing.get('completion', -1))
                
                if prompt_cost == 0 and completion_cost == 0:
                    free_models.append({
                        "id": m.get('id'),
                        "name": m.get('name'),
                        "context_length": m.get('context_length')
                    })
                    
            print(f"Found {len(free_models)} free models.")
            for i, m in enumerate(free_models[:20]):
                print(f"- {m['id']} (Ctx: {m['context_length']})")
                
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    fetch_free_models()
