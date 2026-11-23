# Shell + Browser tools

**مهدی طریری** — mahditariri@gmail.com

## shell_propose
دستور Shell امن/قالبی از درخواست فارسی/انگلیسی می‌سازد — **اجرا نمی‌کند**.

## shell_exec
فقط بعد از Approval Gate · cwd=`workspace` · لیست ممنوع (rm -rf /، curl|bash، …)

## browser_extract / browser_navigate
استخراج متن صفحه / باز کردن در مرورگر · پشت Gate

جریان پیشنهادی: `shell_propose` → نمایش خام → تأیید → `shell_exec`
