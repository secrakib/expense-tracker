# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install uv && uv pip install --system -r requirements.txt
COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]