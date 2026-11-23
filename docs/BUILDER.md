# حالت ساخت (Builder)

مدل می‌تواند داخل **workspace** برای شما پروژه و فایل بسازد.

## دستورات چت

```
/templates
/scaffold my-app python-cli
/scaffold site html-page
/scaffold api python-web
/scaffold case1 osint-case
```

## ابزارهای Agent

- `build_list_templates`
- `build_scaffold(name, template)`
- `build_write_files({ "path": "content", ... })`
- `build_tree(path)`
- به‌همراه `write_file`, `run_python`, `make_zip`

## محدودیت واقع‌بینانه

- کیفیت کد به **قدرت مدل GGUF** شما بستگی دارد (مدل ۷B ضعیف‌تر از مدل بزرگ است).
- ساخت «هر چیزی در دنیا» بدون مدل قوی و بدون تأیید شما ممکن نیست.
- خارج از workspace نیاز به `/elevated on` + تأیید جدا دارد.
