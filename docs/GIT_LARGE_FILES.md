# Git پیشرفته و فایل‌های بزرگ

## در Hub (کشو → Git)

- Status / Diff / Log / Branches / Remotes / Init
- Branch جدید و Checkout
- Commit با تأیید
- **ساخت .gitignore** (مدل‌های gguf، python توکار، payload، sessions، …)
- **اسکن فایل‌های بزرگ** (پیش‌فرض ≥ ۱۰MB)
- Git LFS وضعیت و `track *.gguf`
- Stash

## توصیه

مدل‌های `.gguf` را معمولاً **commit نکنید**. یا در `.gitignore` بمانند یا با **Git LFS**.

```bash
git lfs install
git lfs track "*.gguf"
git add .gitattributes
```
