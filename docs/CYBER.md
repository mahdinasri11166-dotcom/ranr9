# ابزارهای امنیت (دفاعی / تشخیصی)

این ماژول برای تحلیل دارایی‌های مجاز، دیده‌بانی محلی و OSINT غیرفعال است.

| ابزار | کار |
|--------|-----|
| cyber_hash_file | هش MD5/SHA1/SHA256/SHA512 |
| cyber_file_meta | متادیتای فایل |
| cyber_net_local | اینترفیس‌ها و پورت‌های LISTEN همین سیستم |
| cyber_process_security | پروسس‌ها برای triage |
| cyber_dns_full | رکوردهای DNS |
| cyber_http_headers | هدرهای HTTP و امنیتی |
| cyber_tls_info | گواهی TLS |
| cyber_port_check | بررسی چند پورت TCP (هدف مجاز) |
| cyber_nmap | در صورت نصب Nmap روی سیستم |
| cyber_win_events | لاگ ویندوز (Security و ...) |
| cyber_report | ذخیره گزارش Markdown |
| cyber_quick_audit | DNS+HTTP+TLS یک‌جا |

## چت
```
/audit example.com
/hash C:\path\file.exe
/netlocal
این دامنه را از نظر TLS و هدر امنیتی بررسی کن
```

گزارش‌ها: `workspace/security_reports/`

## مرز اخلاقی/قانونی
فقط سیستم‌ها و دامنه‌هایی که مالک آن‌ها هستید یا مجوز دارید.
ابزار brute-force / اکسپلویت عمداً اضافه نشده است.
