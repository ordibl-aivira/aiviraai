FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/worker/ apps/worker/
ENV PYTHONPATH=/app
CMD ["python", "-m", "apps.worker.app.main"]
