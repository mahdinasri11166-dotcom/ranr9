# پرتابل روی GitHub چرا فایل نمی‌داد؟

## علت

ورک‌فلو `release-portable.yml` قبلاً این را اجرا می‌کرد:

```powershell
Compress-Archive -Path * -DestinationPath "GGUF-Runner-portable-....zip"
```

مشکلات:

1. ساخت zip **داخل همان پوشهٔ منبع** با `*` روی ویندوز اغلب خراب/خالی می‌شود یا خودِ zip را قاطی می‌کند.
2. `upload-artifact` بدون `if-no-files-found: error` بود → جاب سبز، **بدون فایل**.
3. روی `workflow_dispatch` فایل به **Release** نمی‌رفت؛ فقط Artifact (اگر ساخته می‌شد). Artifactها را از تب **Actions** همان run باید دانلود کرد، نه از Releases.

## الان

- کپی به `_portable_stage` سپس zip در `_portable_out`
- حداقل حجم ۵۰KB اجباری
- `if-no-files-found: error`
- روی تگ `v*` به Release هم attach می‌شود

## چطور دانلود کنید

1. Actions → **Build portable zip** → Run workflow  
2. بعد از سبز شدن → Artifacts → **GGUF-Runner-portable**  
3. یا با تگ: `git tag v2.9.4 && git push origin v2.9.4` → تب Releases

**توجه:** پرتابل ساده **Python توکار آفلاین ندارد**؛ برای چت بدون نصب جدا، Setup NSIS (`build-nsis.yml`) را بگیرید.
