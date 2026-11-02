FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app \
    && chown app:app /app

COPY --chown=app:app app ./app

USER app

CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host \"$SERVICE_HOST\" --port \"$SERVICE_PORT\""]