FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache \
    DATA_DIR=/data/articles \
    STATE_DIR=/state

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
    && chmod -R a+rX /opt/tiktoken-cache \
    && useradd --uid 10001 --create-home runner \
    && mkdir -p /state /data/articles \
    && chown -R runner:runner /state /data

COPY main.py ./
COPY src/ ./src/
USER runner
ENTRYPOINT ["python", "main.py"]
CMD ["--sync"]
