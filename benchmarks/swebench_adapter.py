from datasets import load_dataset
from typing import Dict, Any, Optional

class SWEBenchAdapter:
    def __init__(self, dataset_name: str = "princeton-nlp/SWE-bench_Lite", split: str = "test"):
        self.dataset_name = dataset_name
        self.split = split
        self._dataset = None

    def _load_dataset(self):
        if self._dataset is None:
            # We load the dataset metadata
            self._dataset = load_dataset(self.dataset_name, split=self.split)

    def get_task_metadata(self, task_id: str) -> Dict[str, Any]:
        """Resolves task metadata without returning hidden evaluation information to the agent layer."""
        self._load_dataset()
        
        for record in self._dataset:
            if record["instance_id"] == task_id:
                return {
                    "task_id": record["instance_id"],
                    "repository": record["repo"],
                    "base_commit": record["base_commit"],
                    "problem_statement": record["problem_statement"],
                    "environment_setup_commit": record.get("environment_setup_commit", ""),
                    "version": record.get("version", ""),
                    "benchmark": "SWE-bench Lite"
                }
        raise ValueError(f"Task ID {task_id} not found in {self.dataset_name}")

    def get_evaluation_metadata(self, task_id: str) -> Dict[str, Any]:
        """Returns the hidden evaluation data. MUST NOT be passed to agents."""
        self._load_dataset()
        
        for record in self._dataset:
            if record["instance_id"] == task_id:
                return {
                    "task_id": record["instance_id"],
                    "test_patch": record["test_patch"],
                    "patch": record["patch"], # Gold patch
                    "FAIL_TO_PASS": record.get("FAIL_TO_PASS", []),
                    "PASS_TO_PASS": record.get("PASS_TO_PASS", [])
                }
        raise ValueError(f"Task ID {task_id} not found in {self.dataset_name}")
