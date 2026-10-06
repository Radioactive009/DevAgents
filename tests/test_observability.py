import unittest
import os
import json
import tempfile
from unittest.mock import patch

from observability.schema import (
    AgentEvent, LLMEvent, ToolEvent, RetrievalEvent, TestEvent, DebugEvent, VerificationEvent, ErrorEvent
)
from observability.telemetry import Telemetry
from observability.logger import sanitize_dict

class TestObservability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = self.temp_dir.name
        self.telemetry = Telemetry(log_dir=self.log_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_lifecycle(self):
        run_id = "test-run-1"
        self.telemetry.start_run(run_id, "task-1", {"use_rag": True}, "groq", "llama-3")
        
        # Add some events
        self.telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="CodingAgent", success=True))
        self.telemetry.record_llm(LLMEvent(run_id=run_id, provider="groq", total_tokens=100))
        self.telemetry.record_tool(ToolEvent(run_id=run_id, tool_name="read_file"))
        
        self.telemetry.end_run(run_id, True, "VERIFIED")
        
        log_file = os.path.join(self.log_dir, f"{run_id}.jsonl")
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, "r") as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 4) # 3 events + 1 summary
        
        # Parse summary
        summary = json.loads(lines[-1])
        self.assertEqual(summary["event_type"], "run_summary")
        self.assertEqual(summary["run_id"], run_id)
        self.assertEqual(summary["total_llm_calls"], 1)
        self.assertEqual(summary["total_tokens"], 100)
        self.assertEqual(summary["total_tool_calls"], 1)
        self.assertEqual(summary["success"], True)
        self.assertEqual(summary["final_status"], "VERIFIED")

    def test_secret_sanitization(self):
        data = {
            "run_id": "test",
            "api_key": "secret123",
            "nested": {
                "PASSWORD": "xyz"
            },
            "list": [{"GROQ_API_KEY": "sk-123"}]
        }
        
        sanitized = sanitize_dict(data)
        self.assertEqual(sanitized["api_key"], "***REDACTED***")
        self.assertEqual(sanitized["nested"]["PASSWORD"], "***REDACTED***")
        self.assertEqual(sanitized["list"][0]["GROQ_API_KEY"], "***REDACTED***")

    def test_missing_token_data(self):
        run_id = "test-run-2"
        self.telemetry.start_run(run_id, "task-2", {})
        
        event = LLMEvent(run_id=run_id, provider="groq", prompt_tokens=None, total_tokens=None)
        self.telemetry.record_llm(event)
        
        log_file = os.path.join(self.log_dir, f"{run_id}.jsonl")
        with open(log_file, "r") as f:
            line = f.readline()
        
        data = json.loads(line)
        self.assertIsNone(data["total_tokens"])
        self.assertIsNone(data["prompt_tokens"])

    def test_log_size_bound(self):
        run_id = "test-run-3"
        self.telemetry.logger.MAX_FILE_SIZE = 100 # Artificially small bound
        
        self.telemetry.start_run(run_id, "task-3", {})
        
        # First event fits
        self.telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="CodingAgent"))
        log_file = os.path.join(self.log_dir, f"{run_id}.jsonl")
        size1 = os.path.getsize(log_file)
        
        # Second event should be ignored due to bound
        self.telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="AnotherAgent", input_summary="A"*1000))
        size2 = os.path.getsize(log_file)
        
        self.assertEqual(size1, size2)

    def test_telemetry_does_not_crash(self):
        # Even with invalid data or permissions, telemetry shouldn't crash the workflow
        self.telemetry.log_dir = "/root/invalid_dir_no_permission"
        try:
            self.telemetry.record_agent(AgentEvent(run_id="test", agent_name="test"))
        except Exception as e:
            self.fail(f"Telemetry crashed with {e}")

if __name__ == "__main__":
    unittest.main()
