FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/organization_service/ apps/organization_service/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.organization_service.app.main:app", "--host", "0.0.0.0", "--port", "8007"]
