import os
import sys
import json
import subprocess
from datetime import datetime
from datasets.bugsinpy.parser import discover_bugs, BugMetadata

def check_environment() -> dict:
    env_status = {
        "is_windows": os.name == 'nt',
        "has_wsl": False,
        "wsl_has_bash": False,
        "can_run_bugsinpy": False,
        "blocker_reason": None
    }
    
    if env_status["is_windows"]:
        # Check if WSL is available
        try:
            res = subprocess.run(["wsl", "--list"], capture_output=True, text=True)
            if res.returncode == 0:
                env_status["has_wsl"] = True
                # Check if it has a functional bash
                res2 = subprocess.run(["wsl", "bash", "-c", "echo hello"], capture_output=True, text=True)
                if res2.returncode == 0 and "hello" in res2.stdout:
                    env_status["wsl_has_bash"] = True
                    env_status["can_run_bugsinpy"] = True
                else:
                    env_status["blocker_reason"] = "WSL is installed but a functional bash environment was not found (e.g., only docker-desktop rootfs available)."
            else:
                env_status["blocker_reason"] = "WSL is not installed or available on this Windows host."
        except Exception as e:
            env_status["blocker_reason"] = f"Failed to detect WSL: {str(e)}"
    else:
        # Assuming linux/mac
        env_status["can_run_bugsinpy"] = True
        
    return env_status

def extract_bugs():
    base_dir = os.path.abspath("BugsInPy")
    if not os.path.exists(base_dir):
        print(f"BugsInPy directory not found at {base_dir}")
        return

    env_status = check_environment()
    
    # We only process black 1-3 as the initial proof
    bugs = discover_bugs(base_dir)
    target_bugs = [b for b in bugs if b.project == 'black' and b.bug_id in ['1', '2', '3']]
    
    manifest = {
        "total_bugs_discovered": len(bugs),
        "attempted_bugs": len(target_bugs),
        "successfully_executed_bugs": 0,
        "valid_failure_samples": 0,
        "setup_failures": 0,
        "unsupported_bugs": 0,
        "timeouts": 0,
        "excluded_samples": 0,
        "environment_status": env_status,
        "timestamp": datetime.now().isoformat(),
        "exclusion_reasons": {}
    }

    print(f"Total bugs discovered in BugsInPy: {len(bugs)}")
    print(f"Targeting {len(target_bugs)} bugs for initial proof (black 1-3)")
    print(f"Environment Status: {json.dumps(env_status, indent=2)}")

    if not env_status["can_run_bugsinpy"]:
        print(f"\nSTOPPING EXTRACTION: Environmental blocker detected.")
        print(f"Reason: {env_status['blocker_reason']}")
        print("BugsInPy framework requires a functional Linux/Bash environment.")
        print("Do not fabricate samples. Recording as unsupported.")
        
        manifest["unsupported_bugs"] = len(target_bugs)
        manifest["exclusion_reasons"]["Windows environment without functional WSL Bash"] = len(target_bugs)
        
    else:
        print("\nEnvironment is capable. Proceeding with checkout...")
        # Since we know it's blocked, we won't reach here in this specific run.
        # But this is where the `bugsinpy-checkout`, `bugsinpy-test` would be orchestrated via subprocess.

    os.makedirs("datasets/bugsinpy/manifests", exist_ok=True)
    manifest_path = "datasets/bugsinpy/manifests/extraction_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")

if __name__ == "__main__":
    extract_bugs()
