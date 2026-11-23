# بیلد GPU

نصب‌کننده استاندارد NSIS روی GitHub **CPU** است.

برای GPU (CUDA):

```bash
pip uninstall llama-cpp-python -y
set CMAKE_ARGS=-DGGML_CUDA=on
pip install llama-cpp-python --no-cache-dir
```

یا wheel از ایندکس‌های CUDA منتشرشده توسط جامعه.

در Hub: GPU layers را ۲۰ / ۳۵ / ‎-۱ بگذارید.
