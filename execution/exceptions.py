class SandboxError(Exception):
    """Base exception for all sandbox errors."""
    pass

class DockerUnavailableError(SandboxError):
    """Raised when Docker daemon is not accessible."""
    pass

class SandboxConfigurationError(SandboxError):
    """Raised when sandbox configuration is invalid."""
    pass
