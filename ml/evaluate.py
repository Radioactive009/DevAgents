import json
import os
from typing import List, Tuple
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

from .schemas import ClassifierMetrics, FailureSample

def evaluate_predictions(y_true: List[str], y_pred: List[str], labels: List[str]) -> ClassifierMetrics:
    accuracy = accuracy_score(y_true, y_pred)
    
    p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average='macro', zero_division=0
    )
    
    p_weighted, r_weighted, f_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average='weighted', zero_division=0
    )
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    
    # Per class metrics
    p_class, r_class, f_class, s_class = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    
    per_class_metrics = {}
    for i, label in enumerate(labels):
        per_class_metrics[label] = {
            "precision": float(p_class[i]),
            "recall": float(r_class[i]),
            "f1": float(f_class[i]),
            "support": int(s_class[i]) if s_class is not None else 0
        }
        
    return ClassifierMetrics(
        accuracy=float(accuracy),
        precision_macro=float(p_macro),
        recall_macro=float(r_macro),
        f1_macro=float(f_macro),
        precision_weighted=float(p_weighted),
        recall_weighted=float(r_weighted),
        f1_weighted=float(f_weighted),
        confusion_matrix=cm.tolist(),
        per_class_metrics=per_class_metrics,
        sample_count=len(y_true)
    )

def save_metrics(metrics: ClassifierMetrics, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    data = {
        "accuracy": metrics.accuracy,
        "precision_macro": metrics.precision_macro,
        "recall_macro": metrics.recall_macro,
        "f1_macro": metrics.f1_macro,
        "precision_weighted": metrics.precision_weighted,
        "recall_weighted": metrics.recall_weighted,
        "f1_weighted": metrics.f1_weighted,
        "confusion_matrix": metrics.confusion_matrix,
        "per_class_metrics": metrics.per_class_metrics,
        "sample_count": metrics.sample_count
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
