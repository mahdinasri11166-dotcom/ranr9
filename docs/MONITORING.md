# ابزارهای مانیتورینگ

| ابزار | کار |
|--------|-----|
| `monitor_system` | نمای کلی سیستم (CPU/RAM/دیسک/آپ‌تایم) |
| `monitor_cpu` | درصد CPU (هر هسته اگر psutil باشد) |
| `monitor_memory` / `mem` | RAM و Swap |
| `monitor_disk` / `disk` | پارتیشن‌ها و فضای آزاد |
| `monitor_network` | ترافیک و اینترفیس‌ها |
| `monitor_processes` | لیست پروسس‌ها (مرتب‌سازی cpu/mem) |
| `monitor_process` | جزئیات یک pid یا نام |
| `monitor_ports` | پورت‌های LISTEN |
| `monitor_uptime` | زمان روشن بودن سیستم |
| `monitor_sensors` | دما / باتری (در صورت پشتیبانی) |
| `monitor_app` | حجم models و workspace برنامه |

## در چت
```
/monitor
/monitor cpu
/monitor mem
/monitor disk
/monitor net
/monitor proc
/monitor ports
/monitor app
```

## پیشنهاد
```bat
python -m pip install psutil
```
با `psutil` خروجی دقیق‌تر و یکدست‌تر است؛ بدون آن از wmic/tasklist/ipconfig استفاده می‌شود.
