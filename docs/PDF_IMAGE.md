# خواندن PDF و تصویر

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## نصب کتابخانه‌ها

```bat
SETUP.bat
```

یا:

```bat
cd scripts\python
python -m pip install -r requirements.txt
```

## کتابخانه‌ها

| کار | پکیج |
|-----|------|
| PDF | `pypdf`, `pymupdf` (PyMuPDF) |
| تصویر | `Pillow` |
| OCR متن از تصویر | `pytesseract` + نصب برنامه [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) |

## استفاده خط فرمان

```bat
cd scripts\python
python file_extract.py C:\path\file.pdf
python file_extract.py C:\path\scan.png --ocr
```

## سرویس محلی (برای UI)

```bat
scripts\start_file_extract.bat
```

- `GET  http://127.0.0.1:8767/health`
- `POST http://127.0.0.1:8767/extract`  
  JSON: `{ "path": "C:/folder/a.pdf", "ocr": true }`

خروجی `text` را در چت paste کنید یا از دکمه فایل در UI استفاده کنید (txt مستقیم؛ PDF از طریق این سرویس).

## محدودیت مرورگر

مرورگر به‌تنهایی PDF را کامل extract نمی‌کند. برای PDF حتماً Python + این اسکریپت را روشن کنید.
