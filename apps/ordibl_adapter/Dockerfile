FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/ordibl_adapter/ apps/ordibl_adapter/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.ordibl_adapter.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
