# درس‌های بیلد نصب‌کننده آفلاین (۷ خطا)

| # | مشکل | راه‌حل در ریپو |
|---|------|----------------|
| 1 | YAML indentation خراب | `build-nsis.yml` از نو، تمیز |
| 2 | llama-server دانلود ۹KB | لینک pinned + fail اگر `< 1MB` |
| 3 | llama-cpp بدون wheel | `--extra-index-url` abetlen CPU + scikit-build-core |
| 4–6 | embed بدون tkinter/tcl | کپی از Python کامل (مسیر از `sys.prefix`) + پچ `._pth` + DLL |
| 7 | tkinter بدون env | در CI: `TCL_LIBRARY`/`TK_LIBRARY`؛ در کاربر: `scripts\env_python.bat` |

## لانچر کاربر نهایی

`CHAT.bat` و `scripts\run_py.bat` قبل از اجرای python صدا می‌زنند:

```bat
call scripts\env_python.bat
```

که برای `python\` توکار تنظیم می‌کند:

- `TCL_LIBRARY=...\python\tcl\tcl8.6`
- `TK_LIBRARY=...\python\tcl\tk8.6`
