import requests

req = {
    "task_description": "Build a Python calculator module with add, subtract, multiply, divide, division-by-zero handling, and pytest tests.",
    "requirements": ["calculator.py", "test_calculator.py"],
    "system": "MULTI_AGENT",
    "provider": "mock",
    "model": "mock-model"
}

try:
    res = requests.post("http://localhost:8000/api/runs", json=req)
    print("Started:", res.json())
except Exception as e:
    print("Error:", e)
