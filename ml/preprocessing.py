import re

def clean_text(text: str) -> str:
    """Basic text cleaning for failure logs and tracebacks."""
    if not text:
        return ""
    
    text = text.lower()
    
    # Remove file paths (often project specific and cause overfitting)
    text = re.sub(r'/[^\s\n]+', ' ', text)
    text = re.sub(r'\\[^\s\n]+', ' ', text)
    
    # Remove hex addresses
    text = re.sub(r'0x[a-f0-9]+', ' ', text)
    
    # Remove line numbers
    text = re.sub(r'line \d+', ' ', text)
    
    # Keep only alphanumeric and basic punctuation
    text = re.sub(r'[^a-z0-9\s_.,-]', ' ', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_features_from_test_result(stdout: str, stderr: str, command: str) -> str:
    """Extracts a combined text representation from test execution outputs."""
    parts = []
    if command:
        parts.append(f"command: {command}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    
    combined = "\n".join(parts)
    return clean_text(combined)
