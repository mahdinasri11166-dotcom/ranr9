# قابلیت‌های پیشرفته v2.5

## پیاده‌سازی‌شده

| قابلیت | ابزار / مسیر |
|--------|----------------|
| Email DNS (MX/SPF/DMARC) | `osint_email_dns` |
| زیردامنه crt.sh + گراف | `osint_crtsh` · `osint_domain_graph` |
| Username موازی + کش + confidence | `osint_username_parallel` |
| Metadata EXIF/PDF | `osint_file_metadata` |
| گزارش HTML فارسی + timeline | `generate_osint_report` → `workspace/osint/reports/` |
| RAG embedding محلی (BoW+numpy) | `rag_build_index` · `rag_local_search` |
| Plugin system | `workspace/plugins/<id>/plugin.json` + `plugin_list` / `plugin_run` |
| Browser فقط خواندنی | `browser_read` + Approval |
| Doctor + ویزارد مدل | `scripts/python/doctor.py` · منوی D |
| CI fail سخت | workflow `build-nsis.yml` |
| NSIS + portable | workflows موجود |

## عمداً پیاده‌سازی‌نشده (سیاست امنیتی)

- **brute-force** / credential stuffing → `bruteforce` همیشه `blocked`
- **اسکنر آسیب‌پذیری تهاجمی** / port scan تهاجمی / exploit → `vuln_scan` همیشه `blocked`

جایگزین دفاعی: گراف دامنه، DNS ایمیل، metadata، browser خواندنی، گزارش.

## نمونه گزارش

```json
{"tool": "generate_osint_report", "arguments": {
  "name": "case1",
  "target": "example.com",
  "data_json": "{\"domain\": {...}, \"crtsh\": {...}}"
}}
```
