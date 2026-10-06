import os
import glob
from dataclasses import dataclass

@dataclass
class BugMetadata:
    project: str
    bug_id: str
    python_version: str
    buggy_commit_id: str
    fixed_commit_id: str
    test_file: str

def parse_bug_info(bug_info_path: str) -> BugMetadata:
    with open(bug_info_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    data = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            val = val.strip('"\'')
            data[key] = val
            
    # Project and bug_id are in the path: BugsInPy/projects/<project>/bugs/<bug_id>/bug.info
    parts = bug_info_path.replace('\\', '/').split('/')
    bug_id = parts[-2]
    project = parts[-4]
    
    return BugMetadata(
        project=project,
        bug_id=bug_id,
        python_version=data.get('python_version', ''),
        buggy_commit_id=data.get('buggy_commit_id', ''),
        fixed_commit_id=data.get('fixed_commit_id', ''),
        test_file=data.get('test_file', '')
    )

def discover_bugs(base_dir: str) -> list[BugMetadata]:
    bugs = []
    pattern = os.path.join(base_dir, "projects", "*", "bugs", "*", "bug.info")
    for bug_info_path in glob.glob(pattern):
        bugs.append(parse_bug_info(bug_info_path))
    return bugs
