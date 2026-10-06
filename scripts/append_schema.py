with open("agents/schema.py", "a") as f:
    f.write('''
@dataclass
class VerificationCriterion:
    criterion_id: str
    requirement_id: str
    description: str
    status: str
    evidence: str
    test_reference: str
    affected_files: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'VerificationCriterion':
        return cls(
            criterion_id=data.get("criterion_id", ""),
            requirement_id=data.get("requirement_id", ""),
            description=data.get("description", ""),
            status=data.get("status", ""),
            evidence=data.get("evidence", ""),
            test_reference=data.get("test_reference", ""),
            affected_files=data.get("affected_files", [])
        )

@dataclass
class VerificationResult:
    status: str
    verified: bool
    summary: str
    criteria: List[VerificationCriterion]
    unmet_requirements: List[str]
    evidence: str
    failed_checks: List[str]
    warnings: List[str]
    requirement_coverage: float
    test_pass_rate: float
    verification_duration: float
    agent_name: str
    provider: Optional[str] = None
    model: Optional[str] = None
    token_usage: Optional[int] = None
    timestamp: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VerificationResult':
        return cls(
            status=data.get("status", ""),
            verified=data.get("verified", False),
            summary=data.get("summary", ""),
            criteria=[VerificationCriterion.from_dict(c) for c in data.get("criteria", [])],
            unmet_requirements=data.get("unmet_requirements", []),
            evidence=data.get("evidence", ""),
            failed_checks=data.get("failed_checks", []),
            warnings=data.get("warnings", []),
            requirement_coverage=data.get("requirement_coverage", 0.0),
            test_pass_rate=data.get("test_pass_rate", 0.0),
            verification_duration=data.get("verification_duration", 0.0),
            agent_name=data.get("agent_name", ""),
            provider=data.get("provider"),
            model=data.get("model"),
            token_usage=data.get("token_usage"),
            timestamp=data.get("timestamp")
        )
''')
