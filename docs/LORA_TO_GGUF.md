# ادغام LoRA و تبدیل به GGUF

بعد از آموزش با `train_lora.py` یک **adapter LoRA** دارید، نه مدل کامل GGUF.
برای استفاده در این رانر باید:

1. Adapter را با مدل پایه **merge** کنید  
2. وزن merge‌شده را به **GGUF** تبدیل کنید  

## پیش‌نیاز

- Python 3.10+
- `transformers`, `peft`, `torch`
- مخزن [llama.cpp](https://github.com/ggml-org/llama.cpp) برای اسکریپت convert

## مرحله ۱ — Merge LoRA با مدل پایه

اسکریپت آماده پروژه:

```bat
cd scripts\python
python merge_lora.py --base Qwen/Qwen2.5-3B-Instruct --lora ..\..\models\lora-out --out ..\..\models\merged-hf
```

خروجی یک پوشه HuggingFace (safetensors) است.

## مرحله ۲ — تبدیل به GGUF

از پوشه llama.cpp (نسخه هم‌خوان با باینری‌تان):

```bat
python convert_hf_to_gguf.py مسیر\models\merged-hf --outfile مسیر\models\my-lora-q8.gguf --outtype q8_0
```

یا برای حجم کمتر:

```bat
python convert_hf_to_gguf.py مسیر\models\merged-hf --outfile مسیر\models\my-lora-q4.gguf --outtype q4_k_m
```

نام اسکریپت ممکن است در نسخه‌های جدید `convert_hf_to_gguf.py` باشد.

## مرحله ۳ — استفاده در Runner

فایل `.gguf` را در پوشه `models` بگذارید و از منو مدل را انتخاب کنید.

## نکات

- Merge روی RAM/VRAM زیاد می‌خواهد (مدل 3B معمولاً با 16GB RAM شدنی است).
- اگر فقط adapter دارید و merge نمی‌کنید، llama.cpp به‌صورت native از بعضی LoRAها پشتیبانی محدود دارد؛ مسیر merge+GGUF مطمئن‌تر است.
- همیشه از **همان مدل پایه‌ای** که LoRA روی آن train شده برای merge استفاده کنید.

## توسعه‌دهنده

مهدی طریری — mahditariri@gmail.com
