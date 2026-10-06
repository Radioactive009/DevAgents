import re

with open("agents/debugging.py", "r") as f:
    content = f.read()

# Add ContextBuilder import
content = content.replace(
    "from orchestration.state import ProjectState",
    "from orchestration.state import ProjectState\nfrom rag.context import ContextBuilder\nfrom rag.schemas import MemoryRecord\nfrom datetime import datetime, timezone"
)

# Replace _build_prompt
new_build_prompt = """
    def _build_prompt(self, state: ProjectState) -> str:
        req_json = ""
        arch_json = ""
        
        if state.project_plan:
            req_json = json.dumps([dataclasses.asdict(r) for r in state.project_plan.requirements], indent=2)
            
        if state.architecture:
            arch_json = json.dumps(dataclasses.asdict(state.architecture), indent=2)
            
        files_json = json.dumps([{ "path": f.path, "content": f.content } for f in state.generated_project.files], indent=2)
        test_json = json.dumps(dataclasses.asdict(state.test_result), indent=2)
        history_json = json.dumps(state.debugging_history, indent=2)
        
        task_info = f"Requirements:\\n{req_json}\\n\\nArchitecture:\\n{arch_json}\\n\\nCurrent Project Files:\\n{files_json}"
        
        retriever = state.metadata.get('retriever')
        memory = state.metadata.get('memory')
        
        rag_chunks = None
        if retriever:
            query = f"{state.test_result.command}\\n{state.test_result.stdout}\\n{state.test_result.stderr}"
            chunks, latency = retriever.retrieve(query, top_k=3)
            rag_chunks = chunks
            state.rag_metadata['last_retrieval'] = {'query': query, 'latency': latency, 'chunks': [c['chunk_id'] for c in chunks]}
            
        memory_records = None
        if memory:
            query = f"{state.test_result.command}\\n{state.test_result.stdout}\\n{state.test_result.stderr}"
            records, latency = memory.retrieve_relevant_memory(query, top_k=3)
            memory_records = records
            state.memory_metadata['last_retrieval'] = {'query': query, 'latency': latency, 'records': [r.memory_id for r in records]}
            
        context_builder = ContextBuilder()
        safe_context = context_builder.build_context(
            task_info=task_info,
            test_result=dataclasses.asdict(state.test_result),
            debug_history=state.debugging_history,
            rag_chunks=rag_chunks,
            memory_records=memory_records
        )
        
        return safe_context + "\\n\\nProvide the exact DebugPatch JSON to fix the failure."
"""

content = re.sub(r'    def _build_prompt\(self, state: ProjectState\) -> str:.*?(?=    def _validate_patch)', new_build_prompt, content, flags=re.DOTALL)

with open("agents/debugging.py", "w") as f:
    f.write(content)

print("Updated debugging.py")
