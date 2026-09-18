# Container image definition for running the FastAPI service.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["fastapi", "run", "src/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
