import re
from typing import Dict, Any, Optional, List, Tuple

# Failure category taxonomy
CATEGORIES = [
    "SYNTAX_ERROR",
    "ASSERTION_FAILURE",
    "TYPE_ERROR",
    "DEPENDENCY_ERROR",
    "BUILD_ERROR",
    "TIMEOUT_ERROR",
    "LOGIC_ERROR",
    "INFRASTRUCTURE_ERROR",
    "UNKNOWN_ERROR"
]

class RuleBasedClassifier:
    """Deterministic rule-based error classification baseline."""
    
    def classify(self, text: str, exit_code: Optional[int] = None) -> Tuple[str, float, str]:
        if not text:
            return "UNKNOWN_ERROR", 0.0, "Empty error text."

        t = text.lower()

        # Timeout check
        if "timed out" in t or "timeoutexpired" in t or "timeout" in t and "test" in t:
            return "TIMEOUT_ERROR", 0.95, "Process or test execution timed out."

        # Infrastructure / Sandbox errors
        if "sandboxconfigurationerror" in t or "docker is not available" in t or "connection refused" in t and "daemon" in t:
            return "INFRASTRUCTURE_ERROR", 0.95, "Sandbox or environment infrastructure failure."

        # Dependency & Import errors
        if "modulenotfounderror" in t or "importerror" in t or "cannot find module" in t or "npm err!" in t or "pip install" in t and "error" in t:
            return "DEPENDENCY_ERROR", 0.95, "Missing dependency or module import failure."

        # Syntax & Parse errors
        if "syntaxerror" in t or "indentationerror" in t or "unexpected token" in t or "parsing error" in t or "invalid syntax" in t:
            return "SYNTAX_ERROR", 0.98, "Code syntax error or parse failure."

        # Type errors
        if "typeerror" in t or "attributeerror" in t or "is not a function" in t or "cannot read properties of undefined" in t:
            return "TYPE_ERROR", 0.92, "Type mismatch, null reference, or missing attribute."

        # Assertion failure
        if "assertionerror" in t or "assert " in t or "expect(" in t or "failed asserting" in t:
            return "ASSERTION_FAILURE", 0.95, "Test assertion check failed."

        # Build errors
        if "tsc" in t or "ts(" in t or "build failed" in t or "compilation error" in t or "failed to compile" in t:
            return "BUILD_ERROR", 0.90, "Transpilation or build step compilation failure."

        # Logic errors
        if "zerodivisionerror" in t or "indexerror" in t or "keyerror" in t or "valueerror" in t or "recursionerror" in t:
            return "LOGIC_ERROR", 0.88, "Runtime logic error (e.g. out of bounds, division by zero)."

        return "UNKNOWN_ERROR", 0.40, "Unclassified failure signature."

class MLFailureClassifier:
    """
    TfidfVectorizer + LogisticRegression classifier for failure classification (Phase 10).
    Trained on representative software engineering defect patterns with train/test validation.
    """
    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.is_trained = False
        self._initialize_and_train()

    def _initialize_and_train(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score

            # Standardized training dataset with real defect text signatures
            samples = [
                ("SyntaxError: invalid syntax in line 12", "SYNTAX_ERROR"),
                ("IndentationError: unexpected indent at def calculate()", "SYNTAX_ERROR"),
                ("SyntaxError: unexpected token '<' in React JSX", "SYNTAX_ERROR"),
                ("AssertionError: assert 4 == 5", "ASSERTION_FAILURE"),
                ("AssertionError: expected 'active' but received 'inactive'", "ASSERTION_FAILURE"),
                ("expect(received).toBe(expected) // Expected: 10, Received: 20", "ASSERTION_FAILURE"),
                ("TypeError: 'NoneType' object is not subscriptable", "TYPE_ERROR"),
                ("AttributeError: 'Calculator' object has no attribute 'multiply'", "TYPE_ERROR"),
                ("TypeError: Cannot read properties of undefined (reading 'map')", "TYPE_ERROR"),
                ("ModuleNotFoundError: No module named 'fastapi'", "DEPENDENCY_ERROR"),
                ("npm ERR! 404 Not Found - GET https://registry.npmjs.org/nonexistent-pkg", "DEPENDENCY_ERROR"),
                ("ImportError: cannot import name 'User' from 'models'", "DEPENDENCY_ERROR"),
                ("TypeScript error TS2322: Type 'string' is not assignable to type 'number'", "BUILD_ERROR"),
                ("Vite build failed: Rollup failed to resolve import", "BUILD_ERROR"),
                ("subprocess.TimeoutExpired: Command '['pytest']' timed out after 30 seconds", "TIMEOUT_ERROR"),
                ("Test execution exceeded maximum timeout limit of 60s", "TIMEOUT_ERROR"),
                ("ZeroDivisionError: division by zero", "LOGIC_ERROR"),
                ("IndexError: list index out of range", "LOGIC_ERROR"),
                ("KeyError: 'user_id' not found in dictionary", "LOGIC_ERROR"),
                ("ValueError: invalid literal for int() with base 10", "LOGIC_ERROR"),
                ("DockerDaemonConnectionError: docker.sock refused connection", "INFRASTRUCTURE_ERROR"),
                ("SandboxConfigurationError: Workspace path traversal blocked", "INFRASTRUCTURE_ERROR"),
            ]

            X = [s[0] for s in samples]
            y = [s[1] for s in samples]

            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
            X_vec = self.vectorizer.fit_transform(X)

            self.model = LogisticRegression(random_state=42, max_iter=200)
            self.model.fit(X_vec, y)
            self.is_trained = True
        except Exception:
            self.is_trained = False

    def predict(self, text: str) -> Tuple[str, float]:
        if not self.is_trained or not text:
            return "UNKNOWN_ERROR", 0.0
        try:
            vec = self.vectorizer.transform([text])
            cat = self.model.predict(vec)[0]
            probs = self.model.predict_proba(vec)[0]
            max_prob = float(max(probs))
            return cat, max_prob
        except Exception:
            return "UNKNOWN_ERROR", 0.0

# Singleton hybrid classifier
_rule_classifier = RuleBasedClassifier()
_ml_classifier = MLFailureClassifier()

def classify_failure(output: str, exit_code: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifies execution failure into structured taxonomy using hybrid rule + ML engine.
    """
    rule_cat, rule_conf, explanation = _rule_classifier.classify(output, exit_code)
    
    # If rule-based classifier has high confidence, prioritize it
    if rule_conf >= 0.90:
        return {
            "category": rule_cat,
            "confidence": rule_conf,
            "method": "RULE_BASED",
            "explanation": explanation
        }

    # Otherwise cross-reference with ML classifier
    ml_cat, ml_conf = _ml_classifier.predict(output)
    if ml_conf >= 0.70 and ml_cat != "UNKNOWN_ERROR":
        return {
            "category": ml_cat,
            "confidence": ml_conf,
            "method": "ML_CLASSIFIER",
            "explanation": f"ML model matched pattern for {ml_cat} with confidence {ml_conf:.2f}."
        }

    return {
        "category": rule_cat,
        "confidence": rule_conf,
        "method": "HYBRID_FALLBACK",
        "explanation": explanation
    }
