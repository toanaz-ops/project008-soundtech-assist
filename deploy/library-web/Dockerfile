# Build from the repo root:  docker build -f deploy/library-web/Dockerfile -t wing-library-web .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY wing_parser ./wing_parser
# Shipped layer = the knowledge/library of the commit this image is built from.
COPY knowledge/library /app/knowledge/library
RUN pip install ".[library-web]" \
    && useradd --create-home --uid 10001 library \
    && mkdir -p /data/library && chown library /data/library

USER library
ENV WING_LIBRARY_DIR=/data/library \
    WING_LIBRARY_SHIPPED_DIR=/app/knowledge/library \
    WING_LIBRARY_AUTH_BASE=https://master.azsoundtech.com
VOLUME /data/library
EXPOSE 8731
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8731/library/healthz', timeout=4).status == 200 else 1)"
CMD ["wing-library-web", "--host", "0.0.0.0", "--port", "8731"]
