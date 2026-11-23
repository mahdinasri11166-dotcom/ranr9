# GGUF Runner v4.2.0

# GGUF Runner v4.0.6

# GGUF Runner

## نصب آسان ویندوز

1. از GitHub Actions فایل **GGUF-Runner-Setup-*.exe** را بگیرید
2. نصب کنید → در پایان برنامه باز می‌شود
3. یا در پوشه پرتابل: **INSTALL.bat**

جزئیات: [نصب.txt](نصب.txt) · [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md)

# GGUF Runner v3.6.1 — App Hub

GGUF Runner v3.0 — App Hub

# GGUF Runner v2.9

**تیم توسعهٔ نو** — مهدی طریری · محسن طریفی

رانر محلی GGUF با چت دسکتاپ، Agent + Approval Gate، OSINT دفاعی، Case، RAG محلی، Plugin و گزارش HTML.

راهنمای Actions/دانلود: [PUBLISH_GITHUB.md](PUBLISH_GITHUB.md)

## نصب

```bat
SETUP.bat
FirstRun.bat
:: یا: GGUF-Runner.bat → W
:: مدل .gguf را در models\ بگذارید (ویزارد راهنمایی می‌کند)
CHAT.bat / START.bat (رابط یکپارچه با کشو)
```

Doctor: `scripts\doctor.bat`

## قابلیت‌های ۲.۶

- سشن: `/sessions` `/open` `/export` ذخیره و خروجی Markdown
- Case OSINT: `/case list|new|export` + ابزارهای `case_*`
- RAG محلی: `/buildrag` `/rag <query>` از books/memory/cases
- OSINT: دامنه، crt.sh، ایمیل DNS، username موازی، metadata، گزارش فارسی
- Plugin در `workspace\plugins\`
- Browser فقط‌خواندنی با Approval
- نصب‌کننده NSIS آفلاین + portable (GitHub Actions با fail سخت)
- ایجنت ۴ لایه (کد، وب، حافظه، سیستم)
- API سازگار با OpenAI روی `http://127.0.0.1:8787/v1` (`scripts\start_openai_api.bat`)
- گراف دامنه SVG داخل گزارش HTML

## عمداً غیرفعال

brute-force و اسکنر آسیب‌پذیری تهاجمی — همیشه `blocked`.

## مجوز

MIT
