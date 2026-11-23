# خطاهای بیلد و رفع‌ها

1. **YAML indentation** — فایل تمیز
2. **llama-server کوچک** — pinned b8581 + رد <1MB
3. **llama-cpp-python** — abetlen CPU wheels
4. **tkinter** — کپی DLL هم در `DLLs\` هم کنار `python.exe` + خط `DLLs` در `._pth`
5. **config_loader / installer module** — فقط `$PWD`؛ تست با فایل موقت کنار python؛ بدون `Set-Location installer`
6. **$root null** — حذف شد؛ همه مسیرها از `$PWD`
7. **Win7** — بسته جدا `python-offline-win7-amd64` → `python38\`
