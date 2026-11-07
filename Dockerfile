# Quick run in a container: Linux, Python 3.11, the locked analysis environment, no Blender. See "Quick run" in README.md.
FROM python:3.11.6-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 libgomp1 libx11-6 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir --no-deps -r requirements.lock.txt && pip check
COPY .git .git
COPY src src
COPY scripts scripts
COPY configs configs
COPY results results
ENTRYPOINT ["python", "scripts/quick_run.py"]
