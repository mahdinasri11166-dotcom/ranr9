# Pipeline یکپارچه LoRA → GGUF

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## مراحل

1. **Export** چت‌های `dataset/**/*.json` → `dataset/auto/alpaca.jsonl`
2. **Train** LoRA روی مدل پایه HF
3. **Merge** adapter با پایه → `models/merged-hf`
4. **Convert** (اختیاری) با `convert_hf_to_gguf.py` → فایل GGUF

## اجرا

```bat
cd scripts\python
python lora_pipeline.py --base Qwen/Qwen2.5-3B-Instruct --epochs 1
```

برای تبدیل خودکار GGUF، مسیر اسکریپت llama.cpp را بدهید:

```bat
python lora_pipeline.py --llama-cpp-convert C:\llama.cpp\convert_hf_to_gguf.py
```

یا یک خط در فایل ریشه پروژه:

`config.llama_cpp_convert.txt`

## حداقل دیتاست

حداقل ۲ جفت instruction/output. با چت و «دیتاست خودکار» در UI جمع می‌شود.

## وضعیت

`models/lora_pipeline_state.json` آخرین مرحله را نگه می‌دارد.

## بعد از GGUF

فایل را در `models\` بگذارید و از منوی Runner انتخاب کنید.
