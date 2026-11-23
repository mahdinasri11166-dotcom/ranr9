# GGUF Runner — API gateway image (Linux). Inference backend is separate.
FROM python:3.11-slim
WORKDIR /app
COPY cloud/gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY cloud/gateway/app.py /app/cloud/gateway/app.py
COPY scripts/python /app/scripts/python
COPY profiles /app/profiles
ENV GGUF_ROOT=/app
ENV GGUF_API_KEYS=dev-key-change-me
EXPOSE 8000
CMD ["uvicorn", "cloud.gateway.app:APP", "--host", "0.0.0.0", "--port", "8000"]
