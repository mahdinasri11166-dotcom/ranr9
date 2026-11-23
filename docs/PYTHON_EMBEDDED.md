# Python توکار (Embedded)

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## ایده

به‌جای نصب Python سیستمی، یک **Python embed** داخل پوشه `python\` قرار می‌گیرد.

| ویندوز | نسخه |
|--------|------|
| Windows 7 | 3.8.10 |
| Windows 8 / 10 / 11 | 3.11.9 |
| معماری | amd64 یا win32 |

## منبع

1. داخل Setup.exe از CI: `installer/payload/*.zip` + `get-pip.py`
2. اگر نبود: دانلود از python.org هنگام SETUP

## اجرا

```bat
SETUP.bat
```

سرویس‌ها از `scripts\run_py.bat` استفاده می‌کنند (اولویت با python\python.exe).
