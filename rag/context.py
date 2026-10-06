import json
from typing import List, Dict, Any, Optional
from rag.schemas import MemoryRecord

class ContextBuilder:
    def __init__(self, max_context_size: int = 15000):
        self.max_context_size = max_context_size

    def build_context(
        self,
        task_info: str,
        test_result: Optional[Dict[str, Any]] = None,
        debug_history: Optional[List[Dict[str, Any]]] = None,
        rag_chunks: Optional[List[Dict[str, Any]]] = None,
        memory_records: Optional[List[MemoryRecord]] = None
    ) -> str:
        parts = []
        
        parts.append("=== CURRENT TASK ===")
        parts.append(task_info)
        
        if rag_chunks:
            parts.append("\n=== PROJECT KNOWLEDGE (RAG) ===")
            seen_content = set()
            for chunk in rag_chunks:
                if chunk['text'] not in seen_content:
                    parts.append(f"--- Source: {chunk.get('source', 'unknown')} ---")
                    parts.append(self._sanitize(chunk['text']))
                    seen_content.add(chunk['text'])

        if memory_records:
            parts.append("\n=== PROJECT MEMORY ===")
            seen_mem = set()
            for rec in memory_records:
                if rec.content not in seen_mem:
                    parts.append(f"[{rec.memory_type}] {rec.timestamp}")
                    parts.append(self._sanitize(rec.content))
                    seen_mem.add(rec.content)
                    
        if test_result:
            parts.append("\n=== TEST RESULT ===")
            parts.append(json.dumps(test_result, indent=2))
            
        if debug_history:
            parts.append("\n=== DEBUG HISTORY ===")
            parts.append(json.dumps(debug_history, indent=2))
            
        full_context = "\n".join(parts)
        
        # Simple character limit, realistically we'd use a tokenizer
        if len(full_context) > self.max_context_size:
            full_context = full_context[:self.max_context_size] + "\n...[CONTEXT TRUNCATED]..."
            
        return full_context
        
    def _sanitize(self, text: str) -> str:
        # A simple sanitization placeholder. In reality this would strip out keys if any sneaked in
        return text
