import unittest
import os
import shutil

from ml.schemas import FailureSample
from ml.preprocessing import clean_text, extract_features_from_test_result
from ml.classifier import FailureClassifier
from ml.evaluate import evaluate_predictions

class TestMLClassifier(unittest.TestCase):
    def setUp(self):
        self.samples = [
            FailureSample("1", "SyntaxError: invalid syntax", "SYNTAX_ERROR", "test", "p1", "1"),
            FailureSample("2", "TypeError: int and str", "TYPE_ERROR", "test", "p1", "2"),
            FailureSample("3", "AssertionError: assert False", "ASSERTION_FAILURE", "test", "p1", "3"),
            FailureSample("4", "SyntaxError: invalid syntax on line 4", "SYNTAX_ERROR", "test", "p1", "4"),
        ]
        self.test_dir = "tests/test_ml_artifacts"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_preprocessing(self):
        text = "File /usr/lib/python/test.py line 42 0x7f8a9b AssertionError: failed"
        cleaned = clean_text(text)
        self.assertNotIn("/usr/lib/python/test.py", cleaned)
        self.assertNotIn("0x7f8a9b", cleaned)
        self.assertNotIn("line 42", cleaned)
        self.assertIn("assertionerror", cleaned)
        
    def test_feature_extraction(self):
        stdout = "output 1"
        stderr = "error 2"
        command = "pytest test.py"
        features = extract_features_from_test_result(stdout, stderr, command)
        self.assertIn("pytest test.py", features)
        self.assertIn("output 1", features)
        self.assertIn("error 2", features)

    def test_classifier_train_predict(self):
        classifier = FailureClassifier()
        classifier.train(self.samples)
        self.assertTrue(classifier.is_trained)
        
        result = classifier.predict("AssertionError: assert 1 == 2")
        self.assertEqual(result.predicted_category, "ASSERTION_FAILURE")
        self.assertGreater(result.confidence, 0.0)
        self.assertIn("ASSERTION_FAILURE", result.probabilities)

    def test_classifier_save_load(self):
        classifier = FailureClassifier()
        classifier.train(self.samples)
        
        model_path = os.path.join(self.test_dir, "model.joblib")
        classifier.save(model_path)
        
        new_classifier = FailureClassifier()
        new_classifier.load(model_path)
        
        self.assertTrue(new_classifier.is_trained)
        result = new_classifier.predict("TypeError: cannot add")
        self.assertEqual(result.predicted_category, "TYPE_ERROR")

    def test_evaluation(self):
        classifier = FailureClassifier()
        classifier.train(self.samples)
        
        metrics = classifier.evaluate(self.samples)
        self.assertEqual(metrics.sample_count, 4)
        self.assertGreaterEqual(metrics.accuracy, 0.0)

    def test_predict_untrained(self):
        classifier = FailureClassifier()
        with self.assertRaises(RuntimeError):
            classifier.predict("test")
            
    def test_empty_input(self):
        classifier = FailureClassifier()
        classifier.train(self.samples)
        
        result = classifier.predict("")
        self.assertEqual(result.predicted_category, "UNKNOWN_ERROR")
        
if __name__ == '__main__':
    unittest.main()
