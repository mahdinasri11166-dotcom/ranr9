# گرفتن llama-server.exe برای Windows 7 / 10 / 11

## Windows 10 و Windows 11 (ساده‌ترین)

1. به صفحه ریلیزهای رسمی بروید:
   https://github.com/ggml-org/llama.cpp/releases

2. آخرین نسخه را پیدا کنید و یکی از این‌ها را دانلود کنید:
   - `llama-bXXXX-bin-win-cpu-x64.zip`          ← فقط CPU
   - `llama-bXXXX-bin-win-cuda-cu12.x-x64.zip`  ← اگر کارت NVIDIA دارید
   - `llama-bXXXX-bin-win-vulkan-x64.zip`       ← برای AMD / Intel

3. محتویات را از حالت فشرده خارج کنید.
4. فایل `llama-server.exe` (و در صورت وجود DLLهای کنارش) را داخل پوشه `bin` برنامه کپی کنید.

## Windows 7 (نیاز به نسخه خاص)

نسخه‌های جدید رسمی روی Win7 کار نمی‌کنند.

از فورک سازگار استفاده کنید:

**مخزن:** https://github.com/Amengh/llama.cpp-windows7

### ساخت از سورس (خلاصه)
1. CMake 3.19.8 (نسخه‌های جدیدتر Win7 را پشتیبانی نمی‌کنند)
2. MinGW-w64 یا Visual Studio 2019
3. کلون و اجرای اسکریپت بیلد طبق راهنمای همان مخزن

سپس `llama-server.exe` ساخته‌شده را در پوشه `bin` قرار دهید.

## نکات مشترک

- روی Win7 همیشه `--host 127.0.0.1` استفاده شود (این برنامه خودش این کار را می‌کند).
- برای CPU خالص مقدار `n_gpu_layers=0` در config.ini کافی است.
- اگر سرور بالا نیامد، با `stop.bat` همه نمونه‌های قبلی را ببندید و دوباره امتحان کنید.
