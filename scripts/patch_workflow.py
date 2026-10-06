import re

with open("orchestration/workflow.py", "r") as f:
    content = f.read()

# Add config parameters to phase7
content = content.replace(
    "    max_debug_iterations: int = 3\n) -> ProjectState:",
    "    max_debug_iterations: int = 3,\n    use_rag: bool = False,\n    use_memory: bool = False\n) -> ProjectState:"
)

# Insert the initialization
init_code = """
    # Phase 8 RAG and Memory Initialization
    from rag.schemas import RAGConfig
    from rag.retriever import Retriever
    from rag.memory import ProjectMemory
    from rag.pipeline import RAGPipeline
    
    rag_config = RAGConfig(use_rag=use_rag, use_memory=use_memory)
    
    retriever = None
    if use_rag:
        pipeline = RAGPipeline(rag_config)
        pipeline.vector_store.load()
        retriever = Retriever(pipeline.embedder, pipeline.vector_store)
        
    memory = None
    if use_memory:
        memory = ProjectMemory(rag_config.memory_store_path)
        
    state.metadata['retriever'] = retriever
    state.metadata['memory'] = memory
    
    # Run the workflow
    state = run_phase6_workflow(
"""

content = content.replace(
    "    state = run_phase6_workflow(\n",
    init_code
)

with open("orchestration/workflow.py", "w") as f:
    f.write(content)

print("Updated workflow.py")
