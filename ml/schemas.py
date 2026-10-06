from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class FailureSample:
    sample_id: str
    text: str
    label: str
    source: str
    project: str
    bug_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassificationResult:
    predicted_category: str
    confidence: float
    probabilities: Dict[str, float]
    model_name: str
    model_version: str
    inference_latency: float

@dataclass
class ClassifierMetrics:
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    precision_weighted: float
    recall_weighted: float
    f1_weighted: float
    confusion_matrix: List[List[int]]
    per_class_metrics: Dict[str, Dict[str, float]]
    sample_count: int
