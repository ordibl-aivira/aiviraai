FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/execution_engine/ apps/execution_engine/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.execution_engine.app.main:app", "--host", "0.0.0.0", "--port", "8013"]
