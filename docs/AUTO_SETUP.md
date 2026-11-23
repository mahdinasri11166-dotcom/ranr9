# نصب خودکار پیش‌نیازها

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## چه چیزی خودکار است؟

| مورد | خودکار؟ |
|------|---------|
| `llama-server.exe` از GitHub (llama.cpp) | بله |
| DLLهای کنار باینری (در صورت وجود در zip) | بله |
| پوشه‌های models/memory/... | بله |
| پکیج‌های Python از `requirements.txt` | اگر Python نصب باشد |
| مدل‌های `.gguf` | **خیر** (حجم و لایسنس) |

## اجرا

- دوبارکلیک **`SETUP.bat`**
- یا اولین بار **`START.bat`** (اگر server نباشد خودش setup را صدا می‌زند)
- یا منوی اصلی گزینه **A**

```bat
powershell -ExecutionPolicy Bypass -File scripts\setup_prereqs.ps1
```

دانلود مجدد اجباری:

```bat
set GGUF_FORCE_DOWNLOAD=1
SETUP.bat
```

## نیازمندی‌ها برای setup

- اینترنت
- PowerShell (ویندوز ۱۰/۱۱ معمولاً هست)
- برای بخش Python: Python 3.10+ در PATH

## منبع دانلود

آخرین releaseهای مخزن:

https://github.com/ggml-org/llama.cpp/releases

اسکریپت zip ویندوز **x64 CPU** را ترجیح می‌دهد (بدون CUDA).  
اگر GPU داری می‌توانی بعداً دستی بیلد CUDA را جایگزین کنی.

## مدل‌ها

مدل را خودت از Hugging Face بگیر و در `models\` بگذار. فقط `.gguf`.
