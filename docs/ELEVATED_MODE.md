# حالت مدیر با تأیید (Elevated Mode)

## فعال‌سازی

1. در چت: `/elevated on`
2. یا در `profiles/approval_policy.json`:
   ```json
   "elevated_mode": true
   ```

## ابزارها (همه REQUIRE_APPROVAL)

| ابزار | کار |
|--------|-----|
| `sys_info` | اطلاعات سیستم |
| `sys_list_dir` | لیست هر مسیر |
| `sys_read_file` | خواندن فایل |
| `sys_write_file` | نوشتن فایل (مسیرهای System32 و مشابه مسدود) |
| `sys_run_cmd` | اجرای دستور شل با تأیید متن کامل |
| `sys_open_path` | باز کردن فایل/پوشه |
| `sys_open_url` | باز کردن URL در مرورگر |

## همچنان مسدود

- brute-force، اسکن تهاجمی
- format / wipe دیسک / diskpart / shutdown دسته‌جمعی
- دزدی credential، keylog، خاموش کردن مخفیانه آنتی‌ویروس

## ریسک

با `elevated_mode=on` مدل می‌تواند **بعد از تأیید شما** دستورات قدرتمند بزند.  
دستور را در پنجره Approval بخوانید؛ اگر مشکوک بود Deny بزنید.
