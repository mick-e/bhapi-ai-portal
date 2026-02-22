FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir dnspython httpx structlog

COPY src/ src/

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 53/udp 53/tcp

CMD ["python", "-m", "src.resolver"]
