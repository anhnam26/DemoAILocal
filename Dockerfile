FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production APP_DATA_DIR=/app/data
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --uid 10001 --create-home appuser
COPY *.py ./
COPY static ./static
COPY knowledge ./knowledge
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
EXPOSE 8088
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/health',timeout=3)"
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8088", "--workers", "1", "--no-proxy-headers"]
