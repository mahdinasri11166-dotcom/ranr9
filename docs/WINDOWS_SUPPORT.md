# پشتیبانی ویندوز

| ویندوز | کلاس | Python | پوشه |
|--------|------|--------|------|
| 7 | legacy | 3.8.10 | `python38\` |
| 8.0 | legacy | 3.8.10 | `python38\` |
| 8.1 | modern | 3.11.9 | `python\` |
| 10 | modern | 3.11.9 | `python\` |
| 11 | modern | 3.11.9 | `python\` |

## خطای api-ms-win-core-path-l1-1-0.dll
یعنی **Python 3.11** روی **Win7** اجرا شده.  
`CHAT.bat` دیگر این ترکیب را مسدود می‌کند و فقط `python38` را می‌پذیرد.

## اگر python38 نیست
Setup را از بیلد Actions جدید نصب کنید (باید هر دو پوشه `python` و `python38` را داشته باشد).
