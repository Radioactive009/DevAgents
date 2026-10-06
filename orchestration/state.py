import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from agents.schema import ProjectPlan, ArchitectureSpecification, GeneratedProject

@dataclass
class ProjectState:
    run_id: str
    user_requirement: str
    project_plan: Optional[ProjectPlan] = None
    architecture: Optional[ArchitectureSpecification] = None
    generated_project: Optional[GeneratedProject] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

