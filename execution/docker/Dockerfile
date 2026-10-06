FROM python:3.11-slim

# Install pytest for test execution
RUN pip install --no-cache-dir pytest

# Create a non-root user for execution safety
RUN useradd -m -s /bin/bash devagent
USER devagent

WORKDIR /app

# The entrypoint will be overridden by the sandbox runner
CMD ["python"]
