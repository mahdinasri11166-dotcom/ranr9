# یادگیری خودکار · یوتیوب · OCR · ترجمه

## ابزارها
| ابزار | کار |
|--------|-----|
| `learn_topic` | سرچ وب + خواندن صفحات + یوتیوب → ذخیره در `workspace/knowledge/` |
| `web_search` / `web_read` | جستجو و خواندن صفحه |
| `youtube_transcript` | زیرنویس/توضیح ویدیو |
| `youtube_search_learn` | جستجوی یوتیوب و یادگیری |
| `save_knowledge` | ذخیره یادداشت |
| `ocr_image` | خواندن متن عکس (نیاز pytesseract یا easyocr) |
| `translate` | ترجمه (MyMemory / LibreTranslate) |
| `social_read` | خواندن صفحه عمومی شبکه‌اجتماعی (اغلب محدود) |

## چت
```
این موضوع را یاد بگیر: انرژی خورشیدی
/learn انرژی خورشیدی
/translate en| سلام دنیا
/ocr C:\path\image.png
```

با Agent روشن، مدل می‌تواند خودش `learn_topic` را صدا بزند.

## محدودیت‌ها
- اینستاگرام/فیس‌بوک معمولاً ربات را بلاک می‌کنند؛ برای کپشن از OCR اسکرین‌شات یا کپی متن استفاده کنید.
- یوتیوب اگر زیرنویس نداشته باشد فقط description گرفته می‌شود.
- OCR: `pip install pytesseract pillow` + نصب Tesseract-OCR روی ویندوز.
