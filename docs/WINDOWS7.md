# ویندوز ۷ و خطای api-ms-win-core-path-l1-1-0.dll

## علت
Python **3.9 و بالاتر** (از جمله 3.11 داخل بیلد قدیمی) به DLLهای ویندوز ۸+ نیاز دارد.  
روی ویندوز ۷ این پیام می‌آید:

`api-ms-win-core-path-l1-1-0.dll is missing`

## راه حل در GGUF Runner
بیلد جدید دو پایتون می‌گذارد:
- `python\` → 3.11 برای ویندوز ۱۰/۱۱
- `python38\` → **3.8.10** برای ویندوز ۷

`CHAT.bat` نسخه ویندوز را تشخیص می‌دهد و روی Win7 از `python38` استفاده می‌کند.

## اگر هنوز خطا می‌بینید
1. Setup را از **بیلد جدید** Actions دوباره نصب کنید  
2. وجود `python38\python.exe` را چک کنید  
3. اختیاری: [VC++ 2015–2022 x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) و به‌روزرسانی Universal CRT (KB2999226)

## محدودیت
ویندوز ۷ رسمی دیگر پشتیبانی نمی‌شود؛ Python 3.8 آخرین گزینه عملی است.
