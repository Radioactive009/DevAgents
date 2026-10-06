import unittest
import os
import json
import tempfile
from unittest.mock import MagicMock

from orchestration.workflow import run_phase11_workflow
from orchestration.state import ProjectState
from observability.telemetry import Telemetry
from llm.base import MockLLMProvider, LLMResponse

class TestPhase11Integration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = self.temp_dir.name
        
        # Inject the test log directory into the global Telemetry instance
        self.telemetry = Telemetry.get_instance(log_dir=self.log_dir)
        self.telemetry.log_dir = self.log_dir
        self.telemetry.logger.log_dir = self.log_dir
        
        self.run_id = "test-phase11-run"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_observability_workflow_integration(self):
        # Mocks
        supervisor_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"requirements": [{"id": "REQ-1", "description": "test"}], "project_name": "test"}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )
        arch_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"components": [{"name": "comp1", "description": "test"}]}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )
        coding_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"files": [{"path": "main.py", "content": "print(1)"}]}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )
        testing_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"test_command": "echo test"}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )
        debugging_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"files_to_modify": []}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )
        verification_mock = MockLLMProvider(
            responses=[LLMResponse(content='{"status": "VERIFIED"}', token_usage={"total_tokens": 10})],
            name="mock", model="mock-model"
        )

        state = run_phase11_workflow(
            run_id=self.run_id,
            user_requirement="Build a test",
            supervisor_provider=supervisor_mock,
            architecture_provider=arch_mock,
            coding_provider=coding_mock,
            testing_provider=testing_mock,
            debugging_provider=debugging_mock,
            verification_provider=verification_mock,
            sandbox_config={"network_enabled": False}
        )

        log_file = os.path.join(self.log_dir, f"{self.run_id}.jsonl")
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, "r") as f:
            lines = [json.loads(line) for line in f.readlines()]
            
        event_types = [e["event_type"] for e in lines]
        self.assertIn("agent", event_types)
        self.assertIn("test", event_types)
        self.assertIn("verification", event_types)
        self.assertIn("run_summary", event_types)
        
        # Check run_summary
        summary = next(e for e in lines if e["event_type"] == "run_summary")
        self.assertEqual(summary["run_id"], self.run_id)
        self.assertEqual(summary["final_status"], "VERIFIED")
        
        # Check that events have unique IDs
        event_ids = [e.get("event_id") for e in lines if "event_id" in e]
        self.assertEqual(len(event_ids), len(set(event_ids)))

if __name__ == "__main__":
    unittest.main()
