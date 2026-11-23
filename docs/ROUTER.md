# روتر هوشمند چندمدلی

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## ایده

دو (یا چند) `llama-server` روی پورت‌های مختلف اجرا می‌شوند.  
سرویس `model_router.py` روی `8770` متن کاربر را طبقه‌بندی می‌کند و درخواست را به بهترین اندپوینت می‌فرستد.

## راه‌اندازی

1. دو مدل را بالا بیاورید:

```bat
start_multi.bat
```

مثلاً مدل عمومی روی 8080 و مدل کدر/ترید روی 8081.

2. روتر:

```bat
scripts\start_router.bat
```

3. در UI اندپوینت را روی Router بگذارید یا از API مستقیم:

`POST http://127.0.0.1:8770/v1/chat/completions`

## تنظیم نقش‌ها

فایل: `profiles/router_config.json`

```json
{
  "endpoints": {
    "general": "http://127.0.0.1:8080",
    "code": "http://127.0.0.1:8081",
    "trade": "http://127.0.0.1:8081"
  },
  "fallback": "http://127.0.0.1:8080",
  "rules": [
    {"role": "code", "patterns": ["کد", "python", "function"]},
    {"role": "trade", "patterns": ["ترید", "بورس", "crypto"]}
  ]
}
```

## API

- `GET /health` — وضعیت هر اندپوینت
- `POST /classify` `{ "text": "..." }`
- `POST /v1/chat/completions` — همان بدنه OpenAI-compatible؛ فیلد اختیاری `force_role`

پاسخ شامل `_router: { role, endpoint }` است.
