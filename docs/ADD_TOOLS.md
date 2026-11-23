# افزودن ابزار دلخواه به GGUF Runner

از نسخه **4.0.6** محدودیت‌های پیش‌فرض ابزار برداشته شده است:

- `approval_policy.json` → `default: ALLOW` ، `blocked_tools: []` ، `elevated_mode: true` ، `unrestricted_tools: true`
- مسیر فایل خارج از `workspace` در حالت unrestricted مجاز است
- سقف تعداد فراخوانی ابزار بالا رفته است

## ۱) سریع‌ترین روش: `workspace/user_tools/`

فایل پایتون بسازید:

```python
# workspace/user_tools/weather_note.py
def run(city: str = "Tehran", **kwargs):
    return {"ok": True, "city": city, "note": "نمونه — منطق خود را اینجا بگذارید"}

TOOLS = {"weather_note": run}
```

برنامه را یک‌بار ببندید و `CHAT.bat` را دوباره اجرا کنید.

## ۲) پلاگین کامل: `workspace/plugins/<id>/`

- `plugin.json` + `run.py` با تابع `run(**kwargs)`
- از ابزار `plugin_run` صدا زده می‌شود

## ۳) تغییر سیاست تأیید

فایل: `profiles/approval_policy.json`

| کلید | معنی |
|------|------|
| `unrestricted_tools` | true = بدون دروازه تأیید پیش‌فرض |
| `elevated_mode` | true = ابزارهای sys_* و مسیر مطلق |
| `default` | ALLOW یا REQUIRE_APPROVAL |
| `blocked_tools` | لیست خالی = هیچ مسدودی داخلی |
| `tools` | فقط برای ابزارهای خاص سطح تعیین کنید |

برای برگرداندن حالت امن‌تر:

```json
{
  "default": "REQUIRE_APPROVAL",
  "unrestricted_tools": false,
  "elevated_mode": false,
  "blocked_tools": []
}
```
