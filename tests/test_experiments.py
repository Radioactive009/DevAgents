import unittest
import os
import json
import tempfile
import yaml
from unittest.mock import patch

from experiments.schema import ExperimentProtocol, TaskManifestEntry
from experiments.runner import ExperimentRunner

class TestExperiments(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manifest_path = os.path.join(self.temp_dir.name, "manifest.json")
        self.protocol_path = os.path.join(self.temp_dir.name, "protocol.yaml")
        
        self.manifest_data = [
            {
                "task_id": "test-1",
                "benchmark": "test",
                "benchmark_version": "1.0",
                "repository": "test/repo",
                "issue_id": "1",
                "task_description": "test",
                "expected_evaluation": "test",
                "difficulty": "easy",
                "inclusion_status": "INCLUDED"
            }
        ]
        
        self.protocol_data = {
            "experiment": {
                "name": "Test Experiment",
                "version": "1.0",
                "research_question": "Test?"
            },
            "benchmark": {
                "name": "Test Benchmark",
                "version": "1.0",
                "task_manifest": self.manifest_path,
                "task_count": 1
            },
            "systems": ["SINGLE_AGENT_BASELINE", "MULTI_AGENT"],
            "llm": {
                "provider": "mock",
                "model": "mock",
                "temperature": 0.0,
                "max_tokens": 100
            },
            "execution": {
                "docker_image": "python:3.11",
                "cpu_limit": 1.0,
                "memory_limit": "1g",
                "timeout_seconds": 10,
                "network_policy": "none",
                "max_debug_iterations": 1
            },
            "reproducibility": {
                "random_seed": 42,
                "git_commit": "abc",
                "prompt_version": "1.0"
            }
        }
        
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest_data, f)
            
        with open(self.protocol_path, "w") as f:
            yaml.dump(self.protocol_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_protocol_loading(self):
        runner = ExperimentRunner(self.protocol_path)
        self.assertEqual(runner.protocol.name, "Test Experiment")
        self.assertEqual(len(runner.protocol.systems), 2)

    def test_manifest_loading(self):
        runner = ExperimentRunner(self.protocol_path)
        self.assertEqual(len(runner.manifest), 1)
        self.assertEqual(runner.manifest[0].task_id, "test-1")

    def test_pre_flight_validation_success(self):
        runner = ExperimentRunner(self.protocol_path)
        # Should not raise
        runner.validate_pre_flight()

    def test_pre_flight_validation_duplicate_task(self):
        self.manifest_data.append(self.manifest_data[0])
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest_data, f)
            
        runner = ExperimentRunner(self.protocol_path)
        with self.assertRaises(ValueError) as ctx:
            runner.validate_pre_flight()
        self.assertIn("Duplicate task ID", str(ctx.exception))

    def test_pre_flight_validation_invalid_system(self):
        self.protocol_data["systems"].append("INVALID_SYSTEM")
        with open(self.protocol_path, "w") as f:
            yaml.dump(self.protocol_data, f)
            
        runner = ExperimentRunner(self.protocol_path)
        with self.assertRaises(ValueError) as ctx:
            runner.validate_pre_flight()
        self.assertIn("Unknown system", str(ctx.exception))

    @patch("experiments.runner.run_single_agent_workflow")
    @patch("experiments.runner.run_phase11_workflow")
    def test_experiment_ordering(self, mock_multi, mock_single):
        runner = ExperimentRunner(self.protocol_path)
        
        # Test deterministic ordering
        systems_called = []
        
        # We mock execute_run to just record the order
        original_execute = runner._execute_run
        
        def mock_execute(task, sys):
            systems_called.append(sys)
            
        runner._execute_run = mock_execute
        
        runner.run_one_task("test-1")
        
        # We check that it called both systems, in a deterministic order for seed 42_test-1
        self.assertEqual(len(systems_called), 2)
        self.assertIn("SINGLE_AGENT_BASELINE", systems_called)
        self.assertIn("MULTI_AGENT", systems_called)
        
        # If we run it again, order should be exactly the same
        systems_called2 = []
        def mock_execute2(task, sys):
            systems_called2.append(sys)
        runner._execute_run = mock_execute2
        runner.run_one_task("test-1")
        
        self.assertEqual(systems_called, systems_called2)

if __name__ == '__main__':
    unittest.main()
