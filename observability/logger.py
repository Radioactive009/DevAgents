import os
import json
import logging
from typing import Dict, Any

def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive information before logging."""
    if not isinstance(d, dict):
        return d
    
    sanitized = {}
    sensitive_keys = {"api_key", "groq_api_key", "openrouter_api_key", "secret", "password", "token", "credential", "private_key"}
    
    for k, v in d.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            sanitized[k] = "***REDACTED***"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            sanitized[k] = v
    return sanitized

class TelemetryLogger:
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB per file

    def __init__(self, log_dir: str = "logs/runs"):
        self.log_dir = log_dir
        
    def _get_log_path(self, run_id: str) -> str:
        return os.path.join(self.log_dir, f"{run_id}.jsonl")
        
    def write_event(self, event_dict: Dict[str, Any]) -> None:
        try:
            run_id = event_dict.get("run_id")
            if not run_id:
                return # Should always have run_id
                
            os.makedirs(self.log_dir, exist_ok=True)
            log_path = self._get_log_path(run_id)
            
            # Simple bounded log
            if os.path.exists(log_path) and os.path.getsize(log_path) > self.MAX_FILE_SIZE:
                return # Log too large, stop logging to avoid blowup
                
            sanitized = sanitize_dict(event_dict)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(sanitized) + "\n")
        except Exception as e:
            # Observability must not crash the workflow
            logging.error(f"Failed to write telemetry event: {str(e)}")
