FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/research_agent/ apps/research_agent/
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.research_agent.app.main:app", "--host", "0.0.0.0", "--port", "8010"]
