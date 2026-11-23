# راهنمای نصب Python برای GGUF Runner

برای **حافظه برداری** و **آموزش LoRA** به Python نیاز دارید.
چت عادی با llama-server بدون Python کار می‌کند.

## Windows 10 / 11 (پیشنهادی)

1. از سایت رسمی دانلود کنید:
   https://www.python.org/downloads/
2. نسخه **3.10 یا 3.11** را بگیرید (پایدارتر برای torch/peft).
3. هنگام نصب گزینه **Add python.exe to PATH** را حتماً فعال کنید.
4. نصب را تمام کنید، سپس Command Prompt جدید باز کنید:

```bat
python --version
pip --version
```

5. پکیج‌های این پروژه:

```bat
cd مسیر\GGUF-Runner\scripts\python
pip install -r requirements.txt
```

اگر GPU انویدیا دارید، torch را مطابق سایت pytorch.org با CUDA نصب کنید.

## Windows 7

- Python رسمی جدید Win7 را پشتیبانی نمی‌کند.
- گزینه‌ها:
  - Python **3.8.10** آخرین نسخه‌ای است که روی Win7 نسبتاً قابل استفاده بود.
  - یا فقط از قابلیت‌های بدون Python استفاده کنید (چت + حافظه متنی).
- حافظه برداری و LoRA روی Win7 توصیه نمی‌شود.

## بررسی سلامت

```bat
python -c "import sys; print(sys.version)"
pip install sentence-transformers faiss-cpu numpy
python memory_server.py
```

باید روی `http://127.0.0.1:8765` بالا بیاید.

## مشکلات رایج

| مشکل | راه‌حل |
|------|--------|
| `python` شناخته نشد | PATH را درست کنید یا از `py -3` استفاده کنید |
| خطای pip SSL | `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt` |
| حافظه کم هنگام install | جمله به جمله نصب کنید: `pip install numpy` سپس بقیه |
| تداخل چند Python | از `py -3.11 -m pip install ...` استفاده کنید |

## توسعه‌دهنده

مهدی طریری — mahditariri@gmail.com


## PDF / Image libraries

Included in requirements.txt: pypdf, pymupdf, Pillow, pytesseract.
Run SETUP.bat after installing Python.
See docs/PDF_IMAGE.md
