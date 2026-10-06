import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from agents.schema import ProjectPlan, ArchitectureSpecification, GeneratedProject, TestResult

@dataclass
class ProjectState:
    run_id: str
    user_requirement: str
    project_plan: Optional[ProjectPlan] = None
    architecture: Optional[ArchitectureSpecification] = None
    generated_project: Optional[GeneratedProject] = None
    test_result: Optional[TestResult] = None
    debugging_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # RAG & Memory
    rag_metadata: Dict[str, Any] = field(default_factory=dict)
    memory_metadata: Dict[str, Any] = field(default_factory=dict)

