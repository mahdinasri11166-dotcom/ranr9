# ساخت ابزار توسط خود مدل

**مهدی طریری** — mahditariri@gmail.com

## ابزارها
| نام | کار |
|-----|-----|
| `create_plugin` | ساخت ابزار جدید (کد پایتون با `def run`) |
| `run_plugin` | اجرای ابزار ساخته‌شده |
| `list_plugins` | لیست |
| `delete_plugin` | حذف |

مسیر: `workspace/agent_plugins/`

## شرط
کد باید تابع `run(...)` داشته باشد.

## محدودیت
Sandbox داخل workspace — دسترسی نامحدود به کل ویندوز نیست.
