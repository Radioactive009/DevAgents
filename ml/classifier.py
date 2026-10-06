import os
import time
import joblib
from typing import List, Dict, Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .schemas import ClassificationResult, FailureSample, ClassifierMetrics
from .preprocessing import extract_features_from_test_result, clean_text
from .evaluate import evaluate_predictions

class FailureClassifier:
    def __init__(self, model_version="1.0"):
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.is_trained = False
        self.labels = []
        self.model_version = model_version
        self.model_name = "tfidf_logreg"

    def train(self, dataset: List[FailureSample]):
        if not dataset:
            raise ValueError("Dataset is empty.")
            
        texts = [clean_text(s.text) for s in dataset]
        y = [s.label for s in dataset]
        
        self.labels = sorted(list(set(y)))
        
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, y)
        self.is_trained = True

    def predict(self, text: str) -> ClassificationResult:
        if not self.is_trained:
            raise RuntimeError("Model is not trained.")
            
        start_time = time.time()
        
        cleaned_text = clean_text(text)
        
        if not cleaned_text:
            return ClassificationResult(
                predicted_category="UNKNOWN_ERROR",
                confidence=1.0,
                probabilities={"UNKNOWN_ERROR": 1.0},
                model_name=self.model_name,
                model_version=self.model_version,
                inference_latency=time.time() - start_time
            )
            
        X = self.vectorizer.transform([cleaned_text])
        
        pred_label = self.model.predict(X)[0]
        probas = self.model.predict_proba(X)[0]
        
        prob_dict = {label: float(prob) for label, prob in zip(self.model.classes_, probas)}
        confidence = prob_dict.get(pred_label, 0.0)
        
        latency = time.time() - start_time
        
        return ClassificationResult(
            predicted_category=pred_label,
            confidence=confidence,
            probabilities=prob_dict,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_latency=latency
        )
        
    def predict_from_test_result(self, stdout: str, stderr: str, command: str) -> ClassificationResult:
        text = extract_features_from_test_result(stdout, stderr, command)
        return self.predict(text)

    def evaluate(self, dataset: List[FailureSample]) -> ClassifierMetrics:
        if not self.is_trained:
            raise RuntimeError("Model is not trained.")
            
        texts = [clean_text(s.text) for s in dataset]
        y_true = [s.label for s in dataset]
        
        X = self.vectorizer.transform(texts)
        y_pred = self.model.predict(X).tolist()
        
        return evaluate_predictions(y_true, y_pred, self.labels)

    def save(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        joblib.dump({
            "vectorizer": self.vectorizer,
            "model": self.model,
            "labels": self.labels,
            "is_trained": self.is_trained,
            "model_version": self.model_version,
            "model_name": self.model_name
        }, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.vectorizer = data["vectorizer"]
        self.model = data["model"]
        self.labels = data["labels"]
        self.is_trained = data["is_trained"]
        self.model_version = data["model_version"]
        self.model_name = data["model_name"]
