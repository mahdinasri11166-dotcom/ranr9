# ابزارهای پیشرفته: شل آزاد · دانلود · API

## شل آزاد

| نام ابزار | توضیح |
|-----------|--------|
| `shell` / `shell_free` / `shell_run` / `cmd` | اجرای هر دستور cmd/shell |
| `shell_powershell` | اجرای اسکریپت PowerShell |

پارامترها: `command`, `cwd` (اختیاری), `timeout` (ثانیه)

در چت:
```
/shell dir
/shell ipconfig
/shell python --version
```

فقط چند الگوی مخرب قطعی (مثل `format c:`) رد می‌شوند.

---

## دانلود فایل

| ابزار | کار |
|--------|-----|
| `download` / `http_download` | شروع دانلود با resume |
| `download_status` / `http_download_status` | پیشرفت |
| `download_list` | لیست |

```
/download https://example.com/file.zip
/downloads
```

---

## API پیشرفته

| ابزار | کار |
|--------|-----|
| `api_request` / `http_request` | هر متد HTTP |
| `api_get` | GET |
| `api_post` | POST + JSON |
| `api_put` | PUT |
| `api_delete` | DELETE |

پارامترهای `api_request`:
- `url`, `method`
- `headers` (dict)
- `json_body` یا `body`
- `params` (query)
- `timeout`, `use_proxy`

در چت:
```
/api GET https://httpbin.org/get
/api POST https://httpbin.org/post {"hello":"world"}
```

از Agent:
```
api_post url=https://api.example.com/v1/data json_body={"x":1} headers={"Authorization":"Bearer TOKEN"}
```

اگر پروکسی چرخشی `enabled` باشد، درخواست‌ها از پروکسی عبور می‌کنند.
