FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/memory_service/ apps/memory_service/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.memory_service.app.main:app", "--host", "0.0.0.0", "--port", "8004"]
