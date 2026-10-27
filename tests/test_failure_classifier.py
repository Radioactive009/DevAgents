import pytest
from evaluation.failure_classifier import classify_failure, RuleBasedClassifier, MLFailureClassifier

def test_rule_based_classifier_categories():
    clf = RuleBasedClassifier()
    assert clf.classify("SyntaxError: invalid syntax")[0] == "SYNTAX_ERROR"
    assert clf.classify("AssertionError: 2 != 3")[0] == "ASSERTION_FAILURE"
    assert clf.classify("ModuleNotFoundError: No module named 'foo'")[0] == "DEPENDENCY_ERROR"
    assert clf.classify("ZeroDivisionError: division by zero")[0] == "LOGIC_ERROR"
    assert clf.classify("subprocess.TimeoutExpired: timed out")[0] == "TIMEOUT_ERROR"

def test_hybrid_classify_failure():
    res = classify_failure("TypeError: 'int' object is not callable")
    assert res["category"] == "TYPE_ERROR"
    assert res["confidence"] > 0.8
    assert res["method"] in ["RULE_BASED", "ML_CLASSIFIER", "HYBRID_FALLBACK"]

def test_classify_empty_string():
    res = classify_failure("")
    assert res["category"] == "UNKNOWN_ERROR"
