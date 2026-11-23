# Piko + Browser Use

**مهدی طریری** — mahditariri@gmail.com

## Browser Use
ابزارها:
- `browser_use_status` — نصب بودن پکیج
- `browser_use` — اجرای تسک مرورگر (نیاز به Approval + تایپ YES)

نصب اختیاری:
```bat
python -m pip install -r scripts\python\requirements-optional.txt
playwright install chromium
```

برای مدل محلی، `model_endpoint` را به سرور OpenAI-compatible بدهید (مثلاً gateway یا llama-server).

## Piko-style (دسکتاپ)
- `piko_plan` — طرح خام اقدامات (اجرا نمی‌کند)
- `piko_act` — یک اقدام مجاز بعد از Gate

اقدامات مجاز: `open_url` · `open_path` · `screenshot` · `type_text` · `hotkey` · `notify`
