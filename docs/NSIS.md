# نصب با NSIS

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## خروجی

`installer/Output/GGUF-Runner-Setup-1.0.0.exe`

## قابلیت‌های نصب‌کننده

- تشخیص Windows 7 / 8 / 8.1 / 10/11
- تشخیص 32-bit / 64-bit
- کپی برنامه در `%LOCALAPPDATA%\GGUF-Runner`
- آیکون دسکتاپ و Start Menu
- اجرای `detect_and_setup.ps1` برای دانلود `llama-server` و pip
- حذف برنامه (Uninstall) — مدل‌های کاربر معمولاً باقی می‌مانند

## ساخت روی ویندوز

1. نصب [NSIS](https://nsis.sourceforge.io/Download)
2. در پوشه `installer`:

```bat
makensis GGUF-Runner.nsi
```

## ساخت با GitHub Actions

ورک‌فلو: **Build NSIS Setup EXE**

```bat
git tag v1.0.0
git push origin v1.0.0
```

یا Actions → Run workflow

## مقایسه با Inno Setup

| | NSIS | Inno |
|--|------|------|
| اسکریپت | `GGUF-Runner.nsi` | `GGUF-Runner.iss` |
| Actions | `build-nsis.yml` | `build-installer.yml` |
| خروجی | همان نام Setup EXE | همان |

هر دو را می‌توانید نگه دارید؛ NSIS سبک و رایج است.
