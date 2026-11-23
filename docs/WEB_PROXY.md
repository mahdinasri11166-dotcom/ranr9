# پروکسی وب پیشرفته

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

پورت: `http://127.0.0.1:8766`

## قابلیت‌ها

- استخراج متن از HTML
- جستجوی DuckDuckGo HTML
- کش فایل‌محور (۱۰ دقیقه)
- مسدودسازی پیش‌فرض localhost/IP خصوصی (ضد SSRF)

## API

### FETCH
```json
POST /fetch
{"url": "https://example.com", "max_chars": 12000, "use_cache": true}
```

### SEARCH
```json
POST /search
{"query": "آب و هوا تهران", "max_chars": 9000}
```

### HEALTH
`GET /health`

## امنیت

به‌صورت پیش‌فرض آدرس‌های خصوصی بلاک هستند. فقط اگر خودتان نیاز دارید:

```json
{"url": "http://127.0.0.1:8080", "allow_private": true}
```

## کش

`memory/proxy_cache/`
