FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
COPY app ./app

FROM base AS dev

RUN pip install --no-cache-dir -e .[dev]

FROM base AS production

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
