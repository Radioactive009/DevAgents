import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
from rag.schemas import MemoryRecord
from datetime import datetime, timezone

class ProjectMemory:
    def __init__(self, store_path: str):
        self.store_path = store_path
        self.records: List[MemoryRecord] = []
        self.load_memory()
        
    def add_memory(self, record: MemoryRecord):
        if not record.timestamp:
            record.timestamp = datetime.now(timezone.utc).isoformat()
        self.records.append(record)
        self._append_to_file(record)
        
    def _append_to_file(self, record: MemoryRecord):
        os.makedirs(os.path.dirname(self.store_path) or '.', exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")
            
    def load_memory(self):
        self.records = []
        if not os.path.exists(self.store_path):
            return
            
        with open(self.store_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    self.records.append(MemoryRecord(**data))
                except Exception:
                    pass # Safely ignore malformed records
                    
    def search_memory(self, query: str, memory_type: Optional[str] = None) -> List[MemoryRecord]:
        results = []
        query_lower = query.lower()
        for r in self.records:
            if memory_type and r.memory_type != memory_type:
                continue
            if query_lower in r.content.lower() or query_lower in (r.source or "").lower():
                results.append(r)
        return results

    def retrieve_relevant_memory(self, query: str, top_k: int = 5, memory_type: Optional[str] = None) -> Tuple[List[MemoryRecord], float]:
        start_time = time.time()
        # Simple BM25 or keyword match could go here, but for now we do naive search
        results = self.search_memory(query, memory_type)
        # Sort by importance and recency
        results.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        latency = time.time() - start_time
        return results[:top_k], latency
