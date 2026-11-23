# حالت Agent v1.7

**مهدی طریری** — mahditariri@gmail.com

## فعال‌سازی
تیک **حالت Agent** در پنل راست یا `/agent`

## ابزارها (داخل workspace)
| ابزار | کار |
|--------|-----|
| write_file / read_file / list_dir | فایل |
| make_zip | ساخت zip |
| run_python | اجرای پایتون محدود |
| web_search / web_fetch | جستجو و خواندن وب (ترجیحاً با proxy :8766) |
| extract_file | PDF / تصویر |
| youtube | متادیتا + زیرنویس (نیاز به yt-dlp) |
| app_settings | فقط تنظیمات همین برنامه |

## محدودیت امنیتی
- نوشتن فقط در `workspace\`
- **تغییر تنظیمات ویندوز / رجیستری / Admin مجاز نیست**

## جلسات
- تاریخچه **بدون سقف**
- تغییر نام جلسه · حذف جلسه

## سرویس‌های کمکی
```bat
scripts\start_all_services.bat
```
Proxy 8766 · PDF 8767 · RAG 8765
