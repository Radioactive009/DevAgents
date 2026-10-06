from benchmarks.swebench_adapter import SWEBenchAdapter

def test_resolve_metadata():
    adapter = SWEBenchAdapter()
    tasks = ["pytest-dev__pytest-11143", "django__django-16816"]
    
    for task_id in tasks:
        meta = adapter.get_task_metadata(task_id)
        print(f"--- Task: {task_id} ---")
        print(f"Repository: {meta['repository']}")
        print(f"Base Commit: {meta['base_commit']}")
        print(f"Version: {meta['version']}")
        print(f"Env Setup Commit: {meta['environment_setup_commit']}")
        assert meta['repository']
        assert meta['base_commit']

        eval_meta = adapter.get_evaluation_metadata(task_id)
        assert eval_meta['test_patch']
        assert eval_meta['patch']
        print(f"Eval patch length: {len(eval_meta['patch'])} chars")

if __name__ == '__main__':
    test_resolve_metadata()
    print("ALL TESTS PASSED")
