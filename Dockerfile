FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml ./
COPY portal_tsinder ./portal_tsinder
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-deps . \
    && useradd --uid 10001 --create-home portal && mkdir -p /data && chown portal /data
USER portal
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "portal_tsinder", "--data-dir", "/data", "serve", "--host", "0.0.0.0"]
