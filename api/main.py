from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import uuid
import asyncio
import mimetypes
from datetime import datetime
import threading

import dotenv
dotenv.load_dotenv(override=True)

from orchestration.workflow import run_phase11_workflow
from llm.factory import create_llm_provider
from observability.telemetry import Telemetry
from orchestration.state import ProjectState

app = FastAPI(title="DevAgents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    task_description: str
    requirements: List[str]
    use_rag: bool = False
    use_memory: bool = False
    use_tools: bool = True
    provider: str = "groq"
    model: Optional[str] = None
    system: str = "MULTI_AGENT"
    human_approval: bool = False

# Global memory to store current runs
active_runs = {}
active_runs_state = {}
run_errors = {}
state_lock = threading.Lock()

def execute_run(run_id: str, request: RunRequest):
    # Respect requested provider and model
    if not request.provider:
        request.provider = "mock"
    
    try:
        # Create providers
        req_text = request.task_description + "\n\nRequirements:\n" + "\n".join(request.requirements)
        
        state_lock.acquire()
        try:
            if run_id not in active_runs_state:
                active_runs_state[run_id] = ProjectState(run_id=run_id, user_requirement=req_text)
            state = active_runs_state[run_id]
            state.metadata["human_approval"] = request.human_approval
            state.metadata["approval_event"] = threading.Event()
            state.metadata["approval_status"] = "PENDING_APPROVAL" if request.human_approval else "NOT_REQUIRED"
        finally:
            state_lock.release()
            
        if request.system == "SINGLE_AGENT_BASELINE":
            from orchestration.workflow import run_single_agent_workflow
            provider = create_llm_provider({"provider": request.provider, "model": request.model})
            # SINGLE_AGENT_BASELINE does not take `state` yet, so it won't be live for MVP Phase 2 unless requested. MVP focuses on Multi-Agent.
            # We'll just run it normally and it'll overwrite.
            final_state = run_single_agent_workflow(
                run_id=run_id,
                user_requirement=req_text,
                provider=provider,
                max_iterations=3
            )
            state_lock.acquire()
            try:
                active_runs_state[run_id] = final_state
            finally:
                state_lock.release()
        else:
            supervisor_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            arch_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            coding_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            testing_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            debugging_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            verification_provider = create_llm_provider({"provider": request.provider, "model": request.model})
            
            run_phase11_workflow(
                run_id=run_id,
                user_requirement=req_text,
                supervisor_provider=supervisor_provider,
                architecture_provider=arch_provider,
                coding_provider=coding_provider,
                testing_provider=testing_provider,
                debugging_provider=debugging_provider,
                verification_provider=verification_provider,
                use_rag=request.use_rag,
                use_memory=request.use_memory,
                use_tools=request.use_tools,
                sandbox_config={"allow_network_for_dependencies": True, "network_enabled": True},
                state=state
            )
        
        telemetry = Telemetry.get_instance()
        record = telemetry.runs.get(run_id)
        failed_statuses = ["SUPERVISOR_FAILED", "ARCHITECTURE_FAILED", "CODING_FAILED", "INFRASTRUCTURE_ERROR", "HUMAN_APPROVAL_REJECTED", "ERROR"]
        if record and getattr(record, "final_status", "") in failed_statuses:
            active_runs[run_id] = "FAILED"
            run_errors[run_id] = (state.metadata.get("coding_error") or 
                                  state.metadata.get("architecture_error") or 
                                  state.metadata.get("supervisor_error") or 
                                  state.metadata.get("testing_error") or 
                                  f"Workflow halted with status: {record.final_status}")
        else:
            active_runs[run_id] = "COMPLETED"
            run_errors[run_id] = None
    except Exception as e:
        print(f"Run failed: {e}")
        import traceback
        traceback.print_exc()
        active_runs[run_id] = "FAILED"
        run_errors[run_id] = str(e)

@app.post("/api/runs")
async def create_run(request: RunRequest):
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    active_runs[run_id] = "RUNNING"
    threading.Thread(target=execute_run, args=(run_id, request), daemon=True).start()
    return {"run_id": run_id, "status": "RUNNING"}

@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    telemetry = Telemetry.get_instance()
    
    record = get_run_record(run_id)
    status = active_runs.get(run_id, "COMPLETED" if record else "UNKNOWN")
    err = run_errors.get(run_id)
    failed_statuses = ["SUPERVISOR_FAILED", "ARCHITECTURE_FAILED", "CODING_FAILED", "INFRASTRUCTURE_ERROR", "HUMAN_APPROVAL_REJECTED", "ERROR"]
    if status == "FAILED" or (status != "RUNNING" and record and getattr(record, "final_status", "") in failed_statuses):
        status = "FAILED"
        if not err:
            state = active_runs_state.get(run_id)
            if state:
                err = (state.metadata.get("coding_error") or 
                       state.metadata.get("architecture_error") or 
                       state.metadata.get("supervisor_error") or 
                       state.metadata.get("testing_error"))
            if not err and getattr(record, "final_status", None):
                err = f"Pipeline halted with status: {record.final_status}"
    else:
        err = None
            
    if record:
        return {
            "run_id": run_id,
            "status": status,
            "configuration": record.configuration,
            "provider": record.provider,
            "model": record.model,
            "duration": getattr(record, "duration_s", None),
            "final_status": getattr(record, "final_status", None),
            "error": err
        }
    return {"run_id": run_id, "status": status, "error": err}

@app.get("/api/runs/{run_id}/events")
async def get_run_events(run_id: str):
    log_path = f"logs/runs/{run_id}.jsonl"
    if not os.path.exists(log_path):
        return {"events": []}
        
    events = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except:
                    pass
    return {"events": events}

def get_run_record(run_id: str):
    telemetry = Telemetry.get_instance()
    record = telemetry.runs.get(run_id)
    if record:
        return record
    log_path = f"logs/runs/{run_id}.jsonl"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get("event_type") == "run_summary":
                            class RecordObj:
                                pass
                            r = RecordObj()
                            for k, v in data.items():
                                setattr(r, k, v)
                            return r
        except Exception:
            pass
    return None

@app.get("/api/runs/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    record = get_run_record(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metrics not found")
        
    return {
        "run_duration": getattr(record, "duration_s", 0),
        "total_llm_calls": getattr(record, "total_llm_calls", 0),
        "total_tokens": getattr(record, "total_tokens", 0),
        "total_tool_calls": getattr(record, "total_tool_calls", 0),
        "total_rag_queries": getattr(record, "total_rag_queries", 0),
        "total_memory_queries": getattr(record, "total_memory_queries", 0),
        "debugging_iterations": getattr(record, "debugging_iterations", 0),
        "test_pass_rate": getattr(record, "test_pass_rate", 0.0),
        "requirement_coverage": getattr(record, "requirement_coverage", 0.0),
        "verification_status": getattr(record, "verification_status", "UNKNOWN")
    }

@app.get("/api/runs")
async def list_runs():
    telemetry = Telemetry.get_instance()
    seen = set()
    runs = []
    # In-memory runs first
    for run_id, record in telemetry.runs.items():
        seen.add(run_id)
        runs.append({
            "run_id": run_id,
            "timestamp": getattr(record, "timestamp_start", None),
            "configuration": getattr(record, "configuration", {}),
            "status": active_runs.get(run_id, "COMPLETED"),
            "final_status": getattr(record, "final_status", None)
        })
    # Add historical runs from disk
    if os.path.exists("logs/runs"):
        for fname in os.listdir("logs/runs"):
            if fname.startswith("run-") and fname.endswith(".jsonl"):
                rid = fname[:-6]
                if rid not in seen:
                    rec = get_run_record(rid)
                    if rec:
                        seen.add(rid)
                        runs.append({
                            "run_id": rid,
                            "timestamp": getattr(rec, "timestamp_start", None),
                            "configuration": getattr(rec, "configuration", {}),
                            "status": "COMPLETED" if getattr(rec, "final_status", "") not in ["SUPERVISOR_FAILED", "ARCHITECTURE_FAILED", "CODING_FAILED", "INFRASTRUCTURE_ERROR", "HUMAN_APPROVAL_REJECTED", "ERROR"] else "FAILED",
                            "final_status": getattr(rec, "final_status", None)
                        })
    runs.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return {"runs": runs}

def get_file_map_for_run(run_id: str) -> dict:
    state = active_runs_state.get(run_id)
    if state and state.generated_project:
        return {f.path.replace("\\", "/"): f.content for f in state.generated_project.files}
    disk_path = f"logs/runs/{run_id}_project.json"
    if os.path.exists(disk_path):
        try:
            with open(disk_path, "r", encoding="utf-8") as pf:
                data = json.load(pf)
                return {f["path"].replace("\\", "/"): f["content"] for f in data.get("files", [])}
        except:
            pass
    return {}

@app.get("/api/runs/{run_id}/project")
async def get_run_project(run_id: str):
    state_lock.acquire()
    try:
        files_copy = get_file_map_for_run(run_id)
        return {"files": files_copy}
    finally:
        state_lock.release()

class ApprovalRequest(BaseModel):
    decision: str  # "APPROVE" or "REJECT"
    feedback: Optional[str] = None

@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, request: ApprovalRequest):
    state_lock.acquire()
    try:
        state = active_runs_state.get(run_id)
        if not state:
            raise HTTPException(status_code=404, detail="Run not found")
        
        event = state.metadata.get("approval_event")
        if not event:
            raise HTTPException(status_code=400, detail="Run does not have a pending approval checkpoint")
            
        decision = request.decision.upper()
        if decision not in ["APPROVE", "REJECT"]:
            raise HTTPException(status_code=400, detail="Decision must be APPROVE or REJECT")
            
        state.metadata["approval_status"] = "APPROVED" if decision == "APPROVE" else "REJECTED"
        if request.feedback:
            state.metadata["approval_feedback"] = request.feedback
            
        event.set()
        return {"status": "SUCCESS", "decision": state.metadata["approval_status"]}
    finally:
        state_lock.release()

@app.get("/api/runs/{run_id}/state")
async def get_run_state(run_id: str):
    import dataclasses
    state_lock.acquire()
    try:
        state = active_runs_state.get(run_id)
        if not state:
            return {"error": "Not found"}
        
        # Safely serialize metadata excluding thread locks/events
        safe_meta = {}
        for k, v in state.metadata.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                safe_meta[k] = v
            else:
                safe_meta[k] = str(v)
                
        return {
            "run_id": run_id,
            "metadata": safe_meta,
            "user_requirement": state.user_requirement,
            "approval_status": state.metadata.get("approval_status", "NOT_REQUIRED"),
            "approval_feedback": state.metadata.get("approval_feedback"),
            "architecture": dataclasses.asdict(state.architecture) if getattr(state, "architecture", None) else None,
            "project_plan": dataclasses.asdict(state.project_plan) if getattr(state, "project_plan", None) else None
        }
    finally:
        state_lock.release()

@app.get("/api/runs/{run_id}/preview-status")
async def get_preview_status(run_id: str):
    state_lock.acquire()
    try:
        file_map = get_file_map_for_run(run_id)
        if not file_map:
            return {"has_preview": False, "status": "NO_PROJECT"}
        
        html_files = [p for p in file_map if p.endswith(".html")]
        if not html_files:
            return {"has_preview": False, "status": "NO_HTML_ENTRYPOINT"}
            
        entrypoint = "index.html" if "index.html" in file_map else html_files[0]
        return {
            "has_preview": True,
            "entrypoint": entrypoint,
            "url": f"/api/runs/{run_id}/preview/{entrypoint}",
            "status": "READY",
            "files_count": len(file_map)
        }
    finally:
        state_lock.release()

@app.get("/api/runs/{run_id}/preview/{file_path:path}")
async def get_preview_file(run_id: str, file_path: str):
    state_lock.acquire()
    try:
        file_map = get_file_map_for_run(run_id)
        if not file_map:
            raise HTTPException(status_code=404, detail="Run project not found")
        
        clean_path = file_path.strip("/").replace("\\", "/")
        
        # If empty or root, look for standard HTML entrypoints
        if not clean_path:
            candidates = ["index.html", "src/index.html", "public/index.html"]
            for c in candidates:
                if c in file_map:
                    clean_path = c
                    break
            if not clean_path:
                html_files = [p for p in file_map if p.endswith(".html")]
                if html_files:
                    clean_path = html_files[0]
                else:
                    raise HTTPException(status_code=404, detail="No HTML entrypoint found in project")

        # Exact match or relative fallback
        matched_content = file_map.get(clean_path)
        if matched_content is None:
            # Fallback by suffix or basename
            for p, content in file_map.items():
                if p.endswith("/" + clean_path) or os.path.basename(p) == os.path.basename(clean_path):
                    matched_content = content
                    break
                    
        if matched_content is None:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found in project")
            
        content_type, _ = mimetypes.guess_type(clean_path)
        if not content_type:
            if clean_path.endswith((".js", ".jsx", ".ts", ".tsx")):
                content_type = "application/javascript"
            elif clean_path.endswith(".css"):
                content_type = "text/css"
            elif clean_path.endswith(".html"):
                content_type = "text/html"
            elif clean_path.endswith(".json"):
                content_type = "application/json"
            else:
                content_type = "text/plain"
                
        return Response(content=matched_content, media_type=content_type)
    finally:
        state_lock.release()

class DeployRequest(BaseModel):
    project_name: Optional[str] = None
    is_private: bool = True
    use_mock: bool = False

@app.get("/api/deployment/config")
async def get_deployment_config():
    from deployment.github_service import GitHubPublishingService
    from deployment.vercel_service import VercelService
    
    gh = GitHubPublishingService()
    vc = VercelService()
    
    gh_status = gh.check_auth()
    vc_status = vc.check_auth()
    
    return {
        "github": gh_status,
        "vercel": vc_status
    }

@app.post("/api/runs/{run_id}/deploy")
async def trigger_run_deployment(run_id: str, request: DeployRequest = DeployRequest()):
    file_map = get_file_map_for_run(run_id)
    if not file_map:
        raise HTTPException(status_code=400, detail="Cannot deploy run: no generated project files found.")
    
    state = active_runs_state.get(run_id)
    project_name = request.project_name
    if not project_name:
        if state and state.user_requirement:
            words = "".join(c if c.isalnum() else " " for c in state.user_requirement[:40]).split()
            project_name = "-".join(words[:4]).lower() or f"devagent-app-{run_id}"
        else:
            project_name = f"devagent-app-{run_id}"
            
    from deployment.manager import DeploymentManager
    manager = DeploymentManager()
    
    def run_deployment_worker():
        manager.deploy_run(
            run_id=run_id,
            project_name=project_name,
            files=file_map,
            is_private=request.is_private,
            use_mock=request.use_mock
        )
        
    threading.Thread(target=run_deployment_worker, daemon=True).start()
    return {"status": "DEPLOYMENT_STARTED", "run_id": run_id, "project_name": project_name}

@app.get("/api/runs/{run_id}/deployment")
async def get_run_deployment(run_id: str):
    from deployment.manager import DeploymentManager
    manager = DeploymentManager()
    record = manager.get_deployment_record(run_id)
    if not record:
        return {"status": "NOT_DEPLOYED", "record": None}
    return {"status": record.stage.value, "record": record.to_dict()}

@app.post("/api/runs/{run_id}/deploy/retry")
async def retry_run_deployment(run_id: str, request: DeployRequest = DeployRequest()):
    return await trigger_run_deployment(run_id, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
