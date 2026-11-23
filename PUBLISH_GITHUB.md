# از GitHub تا آیکون دسکتاپ

**تیم توسعهٔ نو** — مهدی طریری · محسن طریفی

## ۱) آپلود روی GitHub

```bash
git init
git add .
git commit -m "GGUF Runner v4.0.2"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

## ۲) ساخت EXE در Actions

1. در GitHub برو به **Actions**
2. workflow: **Build NSIS Setup EXE (Offline-ready)**
3. **Run workflow** → Run
4. صبر کن تا جاب **سبز** شود (چند دقیقه تا ~۱ ساعت)
5. پایین صفحه جاب → **Artifacts** → **GGUF-Runner-NSIS-Setup** را دانلود کن
6. زیپ Artifact را باز کن → فایل: `GGUF-Runner-Setup-4.0.2.exe`

یا با تگ:

```bash
git tag v4.0.2
git push origin v4.0.2
```

(در این حالت EXE در **Releases** هم می‌آید)

## ۳) نصب روی ویندوز

1. `GGUF-Runner-Setup-4.0.2.exe` را اجرا کن
2. مسیر نصب را تأیید کن
3. تیک **Desktop icon** و **Start Menu** را روشن بگذار (پیش‌فرض روشن است)
4. نصب را تمام کن
5. در پایان می‌توانی «اجرای GGUF Runner» را بزنی

## ۴) آیکون دسکتاپ

بعد از نصب روی دسکتاپ ظاهر می‌شود:

**GGUF Runner.lnk** → همان `CHAT.bat` (App Hub)

دوبار کلیک → برنامه بالا می‌آید.

## ۵) مدل

فایل‌های `.gguf` را در پوشه `models` داخل محل نصب کپی کن، بعد در برنامه از صفحه **مدل‌ها** لود کن.

## اگر Actions قرمز شد

لاگ همان step را بخوان. معمولاً pip / NSIS. دوباره **Re-run** کن.
