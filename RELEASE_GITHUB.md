# انتشار نهایی GGUF Runner v4.7.0

## آپلود
محتوای این زیپ (`ranr7-main/`) را در مخزن GitHub قرار دهید.

## بیلد
1. Actions → **Build NSIS Setup EXE (Offline-ready)** → Run workflow
2. صبر تا سبز شود
3. Artifact: `GGUF-Runner-Setup-4.7.0.exe` (نام ممکن است از version در NSIS بیاید)

## داخل بیلد آفلاین
- Python 3.11 (`python\`) + customtkinter + psutil + llama-cpp-python
- Python 3.8 (`python38\`) برای Windows 7
- Argos Translate + بسته‌های زبانی (در صورت موجود بودن در ایندکس)
- scripts، profiles، docs، user_tools

## بعد از نصب
1. FirstRun / CHAT.bat
2. مدل `.gguf` در `models\`
3. Agent روشن (پیش‌فرض)
4. خروجی‌ها: `workspace\exports\`
5. دانش: `workspace\knowledge\`
6. گزارش امنیتی: `workspace\security_reports\`

## قابلیت‌ها
چت GGUF · Agent خودکار · نیت فارسی · دانلود resume · پروکسی · شل/API · مانیتور · سایبر دفاعی · یادگیری وب/یوتیوب · ترجمه آفلاین · OCR · خروجی کد/DOCX/PDF
