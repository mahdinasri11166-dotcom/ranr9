# نصب روی ویندوز

1. از GitHub Actions فایل **GGUF-Runner-Setup-*.exe** را بگیرید
2. نصب کنید (تیک Desktop icon روشن)
3. در نصب، `install_detect_windows.bat` نسخه ویندوز را ثبت می‌کند
4. مدل `.gguf` → پوشه `models`
5. میانبر دسکتاپ / FirstRun

## Python داخل Setup
| ویندوز | پوشه |
|--------|------|
| 7 / 8.0 | `python38` (3.8.10) |
| 8.1 / 10 / 11 | `python` (3.11.9) |

اگر روی Win7 خطای `api-ms-win-core-path` دیدید، یعنی `python38` نصب نشده — Setup را از بیلد کامل جدید بگیرید.

پیش‌نیازها (pip/tkinter/llama-cpp) داخل EXE آفلاین هستند؛ اینترنت برای اجرای عادی لازم نیست.
