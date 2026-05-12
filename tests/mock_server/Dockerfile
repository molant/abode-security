# Match the test runner's Python version (pyproject.toml requires-python = ">=3.14.2",
# enforced by pytest-homeassistant-custom-component pinning Home Assistant). Keeping
# both runtimes on 3.14 closes the "passes locally on 3.14, fails in mock-docker on
# 3.11" failure mode — most recently `python-socketio==4.6.1`'s `asyncio.wait`
# misuse, which raises TypeError on 3.11+ (deprecated 3.8, removed 3.11).
FROM python:3.14-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Fixtures will be mounted as volume

EXPOSE 8000

# Run server
CMD ["python", "main.py"]
