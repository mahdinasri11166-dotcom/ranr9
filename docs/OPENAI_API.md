# OpenAI-compatible API

```bat
scripts\start_openai_api.bat
```

Base URL: `http://127.0.0.1:8787/v1`

## Endpoints

| Method | Path | توضیح |
|--------|------|--------|
| GET | `/health` | وضعیت |
| GET | `/v1/models` | لیست `.gguf` |
| POST | `/v1/models/load` | `{"model":"file.gguf"}` |
| POST | `/v1/chat/completions` | سازگار با OpenAI Chat |

## نمونه curl

```bash
curl http://127.0.0.1:8787/v1/models
curl http://127.0.0.1:8787/v1/chat/completions -H "Content-Type: application/json" -d "{\"messages\":[{\"role\":\"user\",\"content\":\"سلام\"}],\"max_tokens\":128}"
```

در کلاینت‌هایی مثل Continue / Open WebUI / اسکریپت‌های خودتان:

`api_base = http://127.0.0.1:8787/v1`  
`api_key = anything` (چک نمی‌شود)

مدل اول موجود در `models\` در شروع پیش‌بارگذاری می‌شود.
