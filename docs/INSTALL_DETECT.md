# تشخیص ویندوز هنگام نصب

موقع نصب NSIS اسکریپت زیر اجرا می‌شود:

`scripts\install_detect_windows.bat`

خروجی:
- `profiles\os_class.txt` — legacy یا modern
- `profiles\preferred_python.txt` — `python38` یا `python`
- `installer\detect_log.txt` — جزئیات

| OS | preferred |
|----|-----------|
| Win7 / 8.0 | python38 |
| Win8.1 / 10 / 11 | python |

میانبر دسکتاپ → `FirstRun.bat` (تشخیص + اجرا)
