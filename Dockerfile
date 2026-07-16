FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY matriz_estruturada.json /app/matriz_estruturada.json

ENV PYTHONPATH=/app

RUN mkdir -p uploads

RUN python -m app.scripts.seed_matrix

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
