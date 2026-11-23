# نصب و پیکربندی psutil

`psutil` برای مانیتورینگ دقیق CPU / RAM / دیسک / شبکه / پروسس لازم است (اختیاری ولی توصیه‌شده).

## نصب سریع (ویندوز ۷ با python38)

در Command Prompt:

```bat
cd /d %LOCALAPPDATA%\GGUF-Runner
python38\python.exe -m pip install --upgrade pip
python38\python.exe -m pip install "psutil>=5.9.0"
```

یا دوبار کلیک / اجرا:

```bat
scripts\install_psutil.bat
```

## ویندوز ۱۰ / ۱۱ (python توکار 3.11)

```bat
cd /d %LOCALAPPDATA%\GGUF-Runner
python\python.exe -m pip install "psutil>=5.9.0"
```

## بررسی

```bat
python38\python.exe -c "import psutil; print(psutil.__version__); print(psutil.cpu_percent(0.3)); print(psutil.virtual_memory().percent)"
```

در برنامه:

```
/monitor
/monitor cpu
/doctor
```

Doctor باید بگوید `psutil نصب است`.

## پیکربندی

psutil تنظیم جداگانه‌ای در config.ini ندارد؛ به‌محض نصب، ابزارهای `monitor_*` خودکار از آن استفاده می‌کنند.

اگر نصب نشد (آفلاین):
1. از ماشین دیگر wheel مناسب نسخه پایتون را بگیرید (مثلاً `psutil‑5.9.8‑cp38‑cp38‑win_amd64.whl`)
2. کپی کنید و:

```bat
python38\python.exe -m pip install psutil‑5.9.8‑cp38‑cp38‑win_amd64.whl
```

برای Win7 + Python 3.8.10 معمولاً همان wheelهای `cp38` و `win_amd64` مناسب است.
