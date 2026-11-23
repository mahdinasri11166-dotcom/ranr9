# مسیر ابری (واقع‌بینانه)

**مهدی طریری** — mahditariri@gmail.com

## الان در ریپو
- `cloud/gateway/app.py` — FastAPI: API key، rate limit، chat route، tools با `approved=true`
- `Dockerfile` + `docker-compose.yml`
- `cloud/monitoring/prometheus.yml`
- `cloud/k8s/deployment.yaml` اسکلت

## مراحل پیشنهادی
1. `docker compose up --build gateway`
2. هدر: `X-API-Key: dev-key-change-me`
3. با رشد کاربران: vLLM روی لینوکس+GPU (Safetensors، نه GGUF)
4. سپس K8s + DCGM + Grafana

## محدودیت صادقانه
vLLM روی ویندوز ۷/دسکتاپ GGUF جایگزین کامل نیست؛ مسیر ابری لینوکس/GPU است.
