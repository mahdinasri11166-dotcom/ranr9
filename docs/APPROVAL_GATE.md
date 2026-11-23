# Approval Gate (دروازه تأیید)

**مهدی طریری** — mahditariri@gmail.com

الهام از الگوهای REQUIRE_APPROVAL / BLOCK / ALLOW (مشابه agent-harness، sectrust، sqube-agent-guard، open-action-consent).

## رفتار
| سطح | معنی |
|-----|------|
| **ALLOW** | اجرا بدون سؤال (مثلاً list_dir، read_file) |
| **REQUIRE_APPROVAL** | دیالوگ تأیید در چت قبل از اجرا |
| **BLOCK** | هرگز اجرا نشود |

پیش‌فرض: **fail-closed** — اگر تأیید ممکن نباشد، اجرا نمی‌شود.

## تنظیمات
- فایل: `profiles/approval_policy.json`
- تیک UI: **تأیید همه ابزارها (Gate)** → همه چیز REQUIRE_APPROVAL
- لاگ: `memory/approval_log.jsonl`

## نکته
این لایه جایگزین «اطاعت مطلق بدون خودسری» است: مدل فقط پیشنهاد ابزار می‌دهد؛ **اجرای حساس فقط با تأیید شما**.
