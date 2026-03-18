FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/integration_service/ apps/integration_service/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.integration_service.app.main:app", "--host", "0.0.0.0", "--port", "8005"]
