import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from llm.factory import create_llm_provider

models = [
    'nvidia/nemotron-3.5-lightning:free'
]

for m in models:
    try:
        t0 = time.time()
        p = create_llm_provider({'provider': 'openrouter', 'model': m})
        r = p.generate('Return JSON: {"status": "ok"}')
        print(f'{m}: {time.time()-t0:.2f}s -> {r.text[:40].strip()}')
    except Exception as e:
        print(f'{m} FAILED: {e}')
