import sys
from experiments.runner import ExperimentRunner

def run_pilot():
    runner = ExperimentRunner("configs/experiment_protocol.yaml")
    runner.run_full_experiment()

if __name__ == "__main__":
    run_pilot()
