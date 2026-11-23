# GGUF Runner 4.0.6 — اصلاحات

## مشکلات رفع‌شده

1. **ویندوز ۷ / رابط گرافیکی بالا نمی‌آمد**
   - علت: `customtkinter` داخل `python38` گاهی در بیلد کامل کپی نمی‌شد.
   - اصلاح:
     - در `build-nsis.yml` مرحلهٔ Python 3.8 دیگر `continue-on-error` ندارد.
     - بعد از pip، `import customtkinter` اجباری چک می‌شود؛ در غیر این صورت بیلد fail می‌شود.
     - در NSIS کپی `python38` دیگر `/nonfatal` نیست.
   - در `CHAT.bat`: اگر customtkinter نبود یک‌بار `pip install customtkinter` امتحان می‌شود.

2. **رابط بدون مدل هم باز می‌شود**
   - `FirstRun.bat` دیگر فقط به خاطر خالی بودن `models\` متوقف نمی‌شود.
   - پیام راهنما نشان داده می‌شود و Hub بالا می‌آید.

3. **پاسخ بدون مدل محلی**
   - اگر مدل GGUF لود نباشد، چت از **RAG محلی (پوشه books + memory)** و **جستجوی وب (DuckDuckGo)** پاسخ ترکیبی می‌سازد.
   - برای پاسخ کامل‌تر بعداً یک `.gguf` در `models\` بگذارید و از صفحه «مدل‌ها» لود کنید.

## ساخت EXE جدید

1. این مخزن را push کنید (یا تگ `v4.0.6`).
2. در GitHub Actions ورک‌فلو **Build NSIS Setup EXE** را اجرا کنید.
3. از Artifacts / Release فایل `GGUF-Runner-Setup-4.0.6.exe` را بگیرید و نصب کنید.

## روی سیستم فعلی (بدون بیلد جدید)

اگر اینترنت دارید:

```bat
cd /d %LOCALAPPDATA%\GGUF-Runner
python38\python.exe -m pip install customtkinter
CHAT.bat
```

