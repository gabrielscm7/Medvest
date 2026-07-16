FROM node:24-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY matriz_estruturada.json /app/matriz_estruturada.json
COPY --from=frontend /app/dist /app/frontend_dist

ENV PYTHONPATH=/app
ENV FRONTEND_DIR=/app/frontend_dist

RUN mkdir -p uploads
RUN python -m app.scripts.seed_matrix

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
