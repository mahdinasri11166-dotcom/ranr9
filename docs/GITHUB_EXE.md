# ساخت EXE روی GitHub

**مهدی طریری** — mahditariri@gmail.com

## مراحل
1. کد را روی GitHub Push کنید.
2. Actions → **build-nsis** (یا نام workflow موجود) → Run workflow  
   یا تگ بزنید: `git tag v1.8.0 && git push --tags`
3. Artifact: `GGUF-Runner-NSIS-Setup`  
   یا در Releases فایل `GGUF-Runner-Setup-1.8.0.exe`

## بعد از نصب برای کاربر نهایی
1. اجرای First Run / SETUP (Python + کتابخانه‌ها)
2. کپی `.gguf` → `models\`
3. CHAT.bat — تنظیم پارامترها از پنل راست

## نکته
GitHub مدل GGUF را داخل EXE نمی‌گذارد (حجم خیلی زیاد).
