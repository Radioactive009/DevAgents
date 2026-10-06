import os
import argparse
from sklearn.model_selection import train_test_split

from ml.dataset import load_dataset, save_dataset, generate_synthetic_bugsinpy_dataset
from ml.classifier import FailureClassifier
from ml.evaluate import save_metrics

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", type=str, default="ml/artifacts/dataset.json")
    parser.add_argument("--model-path", type=str, default="ml/artifacts/model.joblib")
    parser.add_argument("--metrics-path", type=str, default="ml/artifacts/metrics.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generate-synthetic", action="store_true")
    
    args = parser.parse_args()
    
    if args.generate_synthetic:
        print(f"Generating synthetic dataset at {args.data_path}")
        dataset = generate_synthetic_bugsinpy_dataset()
        save_dataset(dataset, args.data_path)
    else:
        print(f"Loading dataset from {args.data_path}")
        dataset = load_dataset(args.data_path)
        
    if not dataset:
        print("Dataset is empty. Exiting.")
        return

    # Train test split
    print(f"Splitting dataset (test_size={args.test_size}, seed={args.seed})")
    
    labels = [s.label for s in dataset]
    # Simple split, could use stratify if classes are large enough
    try:
        train_data, test_data = train_test_split(dataset, test_size=args.test_size, random_state=args.seed, stratify=labels)
    except ValueError:
        print("Warning: Could not stratify due to small class counts. Using random split.")
        train_data, test_data = train_test_split(dataset, test_size=args.test_size, random_state=args.seed)
        
    print(f"Train size: {len(train_data)}")
    print(f"Test size: {len(test_data)}")
    
    # Train
    print("Training classifier...")
    classifier = FailureClassifier()
    classifier.train(train_data)
    
    # Evaluate
    print("Evaluating classifier...")
    metrics = classifier.evaluate(test_data)
    
    print(f"Accuracy: {metrics.accuracy:.4f}")
    print(f"Macro F1: {metrics.f1_macro:.4f}")
    
    # Save
    print(f"Saving model to {args.model_path}")
    classifier.save(args.model_path)
    
    print(f"Saving metrics to {args.metrics_path}")
    save_metrics(metrics, args.metrics_path)

if __name__ == "__main__":
    main()
