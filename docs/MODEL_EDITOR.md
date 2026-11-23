# ویرایش مدل در رابط گرافیکی

## مهم
فایل‌های **GGUF باینری** (وزن شبکه) اینجا عوض نمی‌شوند.  
برای هر مدل یک فایل تنظیمات کنار آن ساخته می‌شود:

`models/YourModel.gguf.meta.json`

## از رابط
1. صفحه **مدل‌ها**
2. روی مدل دکمه **ویرایش**
3. تغییر:
   - نام نمایشی
   - n_ctx / GPU layers / threads
   - temperature, max_tokens, top_p, repeat_penalty
   - System Prompt مخصوص همان مدل
   - یادداشت و علاقه‌مندی
   - تغییر نام فایل `.gguf`
4. **ذخیره** یا **ذخیره و لود**

با لود بعدی مدل، تنظیمات sidecar خودکار اعمال می‌شود.

## ابزار Agent
- `model_meta_get` / `model_meta_save`
- `model_meta_list`
- `model_rename` / `model_duplicate`
