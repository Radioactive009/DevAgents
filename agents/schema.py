from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
import re

@dataclass
class Requirement:
    id: str
    description: str
    priority: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Requirement':
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            priority=data.get("priority", "")
        )

@dataclass
class Task:
    id: str
    description: str
    dependencies: List[str]
    expected_output: str
    requirement_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            expected_output=data.get("expected_output", ""),
            requirement_ids=data.get("requirement_ids", [])
        )

@dataclass
class ProjectPlan:
    project_summary: str
    requirements: List[Requirement]
    non_functional_requirements: List[str]
    tasks: List[Task]
    testing_requirements: List[str]
    assumptions: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectPlan':
        return cls(
            project_summary=data.get("project_summary", ""),
            requirements=[Requirement.from_dict(r) for r in data.get("requirements", [])],
            non_functional_requirements=data.get("non_functional_requirements", []),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            testing_requirements=data.get("testing_requirements", []),
            assumptions=data.get("assumptions", [])
        )

@dataclass
class TechnologyStack:
    language: str
    framework: str
    database: str
    other: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'TechnologyStack':
        return cls(
            language=data.get("language", ""),
            framework=data.get("framework", ""),
            database=data.get("database", ""),
            other=data.get("other", [])
        )

@dataclass
class ArchitectureComponent:
    name: str
    responsibility: str
    dependencies: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'ArchitectureComponent':
        return cls(
            name=data.get("name", ""),
            responsibility=data.get("responsibility", ""),
            dependencies=data.get("dependencies", [])
        )

@dataclass
class ArchitectureDecision:
    decision: str
    reason: str
    requirement_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ArchitectureDecision':
        return cls(
            decision=data.get("decision", ""),
            reason=data.get("reason", ""),
            requirement_ids=data.get("requirement_ids", [])
        )

@dataclass
class ArchitectureSpecification:
    project_type: str
    technology_stack: TechnologyStack
    components: List[ArchitectureComponent]
    apis: List[str]
    data_models: List[str]
    directory_structure: List[str]
    dependencies: List[str]
    configuration: List[str]
    security_considerations: List[str]
    testing_strategy: List[str]
    architecture_decisions: List[ArchitectureDecision] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'ArchitectureSpecification':
        return cls(
            project_type=data.get("project_type", ""),
            technology_stack=TechnologyStack.from_dict(data.get("technology_stack", {})),
            components=[ArchitectureComponent.from_dict(c) for c in data.get("components", [])],
            apis=data.get("apis", []),
            data_models=data.get("data_models", []),
            directory_structure=data.get("directory_structure", []),
            dependencies=data.get("dependencies", []),
            configuration=data.get("configuration", []),
            security_considerations=data.get("security_considerations", []),
            testing_strategy=data.get("testing_strategy", []),
            architecture_decisions=[ArchitectureDecision.from_dict(d) for d in data.get("architecture_decisions", [])]
        )

def parse_json_response(text: str) -> dict:
    # Attempt to extract JSON from code blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Try parsing the whole thing
    return json.loads(text)

@dataclass
class GeneratedFile:
    path: str
    content: str
    description: str = ""
    requirement_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'GeneratedFile':
        return cls(
            path=data.get("path", ""),
            content=data.get("content", ""),
            description=data.get("description", ""),
            requirement_ids=data.get("requirement_ids", [])
        )

@dataclass
class GeneratedProject:
    project_name: str
    files: List[GeneratedFile]
    entrypoint: str
    run_command: str
    test_command: str
    dependencies: List[str]
    requirement_coverage: Dict[str, List[str]]

    @classmethod
    def from_dict(cls, data: dict) -> 'GeneratedProject':
        return cls(
            project_name=data.get("project_name", ""),
            files=[GeneratedFile.from_dict(f) for f in data.get("files", [])],
            entrypoint=data.get("entrypoint", ""),
            run_command=data.get("run_command", ""),
            test_command=data.get("test_command", ""),
            dependencies=data.get("dependencies", []),
            requirement_coverage=data.get("requirement_coverage", {})
        )
