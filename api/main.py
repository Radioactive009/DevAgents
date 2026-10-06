from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import uuid
import asyncio
from datetime import datetime
import threading

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
    model: str = "llama3-70b-8192"
    system: str = "MULTI_AGENT"

# Global memory to store current runs
active_runs = {}
active_runs_state = {}
state_lock = threading.Lock()

def execute_run(run_id: str, request: RunRequest):
    try:
        # Create providers
        req_text = request.task_description + "\n\nRequirements:\n" + "\n".join(request.requirements)
        
        state_lock.acquire()
        try:
            if run_id not in active_runs_state:
                active_runs_state[run_id] = ProjectState(run_id=run_id, user_requirement=req_text)
            state = active_runs_state[run_id]
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
                state=state
            )
        
        active_runs[run_id] = "COMPLETED"
    except Exception as e:
        print(f"Run failed: {e}")
        active_runs[run_id] = "FAILED"

@app.post("/api/runs")
async def create_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    active_runs[run_id] = "RUNNING"
    background_tasks.add_task(execute_run, run_id, request)
    return {"run_id": run_id, "status": "RUNNING"}

@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    telemetry = Telemetry.get_instance()
    
    status = active_runs.get(run_id, "COMPLETED" if run_id in telemetry.runs else "UNKNOWN")
    
    record = telemetry.runs.get(run_id)
    if record:
        return {
            "run_id": run_id,
            "status": status,
            "configuration": record.configuration,
            "provider": record.provider,
            "model": record.model,
            "duration": getattr(record, "duration_s", None),
            "final_status": getattr(record, "final_status", None)
        }
    return {"run_id": run_id, "status": status}

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

@app.get("/api/runs/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    telemetry = Telemetry.get_instance()
    record = telemetry.runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Metrics not found")
        
    return {
        "run_duration": getattr(record, "duration_s", 0),
        "total_llm_calls": record.total_llm_calls,
        "total_tokens": getattr(record, "total_tokens", 0),
        "total_tool_calls": record.total_tool_calls,
        "total_rag_queries": record.total_rag_queries,
        "total_memory_queries": getattr(record, "total_memory_queries", 0),
        "debugging_iterations": record.debugging_iterations,
        "test_pass_rate": getattr(record, "test_pass_rate", 0.0),
        "requirement_coverage": getattr(record, "requirement_coverage", 0.0),
        "verification_status": getattr(record, "verification_status", "UNKNOWN")
    }

@app.get("/api/runs")
async def list_runs():
    telemetry = Telemetry.get_instance()
    runs = []
    for run_id, record in telemetry.runs.items():
        runs.append({
            "run_id": run_id,
            "timestamp": record.timestamp_start,
            "configuration": record.configuration,
            "status": active_runs.get(run_id, "COMPLETED"),
            "final_status": getattr(record, "final_status", None)
        })
    return {"runs": list(reversed(runs))}

@app.get("/api/runs/{run_id}/project")
async def get_run_project(run_id: str):
    state_lock.acquire()
    try:
        state = active_runs_state.get(run_id)
        if not state or not state.generated_project:
            return {"files": {}}
        # Create a deep copy of the files list to avoid iteration over mutated list
        files_copy = {f.path: f.content for f in state.generated_project.files}
        return {"files": files_copy}
    finally:
        state_lock.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
