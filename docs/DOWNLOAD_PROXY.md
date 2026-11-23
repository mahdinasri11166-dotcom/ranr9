# دانلودر قابل‌ازسرگیری + پروکسی چرخشی

## دانلودر

ابزارها (در Agent یا از طریق `execute_tool`):

| ابزار | کار |
|--------|-----|
| `download` / `download_start` | شروع دانلود از URL |
| `download_status` | وضعیت + نوار پیشرفت |
| `download_list` | همه Jobها |
| `download_resume` | ادامه بعد از قطع |
| `download_cancel` | لغو |

### ویژگی‌ها
- ذخیره موقت `.part` + متادیتا در `workspace/downloads/.state/`
- پشتیبانی **HTTP Range** برای resume
- اگر اینترنت قطع شود وضعیت `retrying` می‌شود و **خودکار** هر چند ثانیه دوباره تلاش می‌کند تا تمام شود یا `download_cancel` بزنید
- خروجی نهایی: `workspace/downloads/`
- در صورت فعال بودن پروکسی، از استخر پروکسی استفاده می‌کند

### مثال
```
download url=https://example.com/file.zip
download_status job_id=abc123
download_list
```

خروجی status شامل `progress_bar` شبیه:
`[########------------]  40.0%` و سرعت انسانی است.

---

## پروکسی چرخشی

فایل تنظیم: `workspace/proxies.json` (یا `profiles/proxies.json`)

```json
{
  "enabled": true,
  "rotate": "per_request",
  "proxies": [
    "http://user:pass@1.2.3.4:8080",
    "http://5.6.7.8:3128",
    "socks5://127.0.0.1:9050"
  ]
}
```

یا فایل متنی `workspace/proxies.txt` (هر خط یک پروکسی).

| ابزار | کار |
|--------|-----|
| `proxy_add` | افزودن پروکسی |
| `proxy_remove` | حذف |
| `proxy_list` | لیست |
| `proxy_enable` | روشن/خاموش (`enabled=true/false`) |
| `proxy_test` | تست یک پروکسی |
| `proxy_next` | پروکسی بعدی در چرخش |

`rotate`:
- `per_request` — به نوبت
- `random` — تصادفی

وقتی `enabled: true` باشد، درخواست‌های OSINT / جستجوی وب و دانلود از پروکسی استفاده می‌کنند.

### مثال
```
proxy_add proxy=http://1.2.3.4:8080
proxy_enable enabled=true
proxy_test
proxy_list
```

برای SOCKS5 بهتر است بسته `PySocks` نصب باشد؛ در غیر این صورت HTTP/HTTPS proxy توصیه می‌شود.
