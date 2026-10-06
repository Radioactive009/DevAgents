import unittest
import os
import yaml
import json
from llm.base import MockLLMProvider
from experiments.runner import ExperimentRunner, ExperimentLogger
from evaluation.metrics import task_success_rate, test_pass_rate

class TestFoundation(unittest.TestCase):
    def test_mock_llm_provider(self):
        provider = MockLLMProvider()
        response = provider.generate("Hello")
        self.assertEqual(response.text, "This is a mock LLM response.")

    def test_config_loading(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "experiment_config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.assertIn("experiment_name", config)
        self.assertIn("configuration", config)
        self.assertIn("llm_provider", config)

    def test_experiment_runner(self):
        config = {
            "experiment_name": "test_exp",
            "configuration": "SINGLE_AGENT_BASELINE",
            "llm_provider": "mock",
            "llm_model": "mock-model"
        }
        
        log_dir = os.path.join(os.path.dirname(__file__), "test_logs")
        logger = ExperimentLogger(log_dir=log_dir)
        runner = ExperimentRunner(config=config, logger=logger)
        
        task = {"id": "task_1"}
        result = runner.run_experiment(task)
        
        self.assertIn("run_id", result)
        self.assertEqual(result["experiment_id"], "test_exp")
        
        # Verify JSONL logging
        log_file = os.path.join(log_dir, "runs.jsonl")
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)
            last_record = json.loads(lines[-1])
            self.assertEqual(last_record["run_id"], result["run_id"])
            
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)
        if os.path.exists(log_dir):
            os.rmdir(log_dir)

    def test_metrics(self):
        runs = [
            {"task_success": True, "tests_total": 10, "tests_passed": 10},
            {"task_success": False, "tests_total": 10, "tests_passed": 5}
        ]
        
        self.assertEqual(task_success_rate(runs), 0.5)
        self.assertEqual(test_pass_rate(runs), 15/20)

if __name__ == '__main__':
    unittest.main()
