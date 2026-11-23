# فرمت MNN در برابر GGUF

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## خلاصه

| فرمت | موتور اجرا | مناسب برای |
|------|------------|------------|
| **GGUF** | llama.cpp / این پروژه (`llama-server`) | PC ویندوز، چت دسکتاپ |
| **MNN** | Alibaba MNN | موبایل، تبلت، edge |

**GGUF Runner فقط فایل‌های `.gguf` را اجرا می‌کند.**  
مدل‌های `.mnn` در این برنامه لود نمی‌شوند.

---

## MNN چیست؟

**MNN** (Mobile Neural Network) موتور استنتاج سبک ساختهٔ **علی‌بابا** است.  
فرمت مدل آن معمولاً پسوند `.mnn` دارد و برای اجرای روی دستگاه با کتابخانه MNN طراحی شده است.

### سیستم‌عامل‌های رایج MNN

- Android (حدود 4.3+)
- iOS / iPadOS (حدود 8.0+)
- لینوکس / ویندوز / امبدد با رابط POSIX (پشتیبانی هست؛ تمرکز اصلی موبایل است)

### سخت‌افزار

| بخش | مثال |
|-----|------|
| CPU | ARM گوشی، x86/x64 روی PC |
| GPU | OpenCL، Vulkan، Metal (اپل)، CUDA |
| NPU | در بعضی گوشی‌ها: CoreML، Huawei HiAI، NNAPI، Qualcomm QNN |

MNN برای اپ‌های موبایل (مثل سناریوهای on-device در اکوسیستم علی‌بابا) و مدل‌های کوچک/متوسط روی گوشی بهینه شده است.

منبع: [alibaba/MNN](https://github.com/alibaba/MNN)

---

## GGUF چیست؟

**GGUF** فرمت رایج مدل برای **llama.cpp** و ابزارهای سازگار است:

- LM Studio
- Ollama (در مسیرهای خاص)
- این پروژه: `bin\llama-server.exe`

فایل‌ها پسوند `.gguf` دارند و quantهایی مثل `Q4_K_M`، `Q5_K_M` روی نام فایل دیده می‌شود.

---

## اگر مدل MNN داری چه کار کنی؟

1. همان مدل پایه را در Hugging Face پیدا کن.
2. نسخه **GGUF** را دانلود کن (ترجیحاً `Q4_K_M`).
3. فایل را در پوشه `models\` این پروژه بگذار.
4. با `START.bat` اجرا کن.

### مثال

مدل:

`Qwen2.5-Coder-3B-Instruct-abliterated-MNN` → در این رانر کار نمی‌کند.

جایگزین GGUF:

- [bartowski/Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/bartowski/Qwen2.5-Coder-3B-Instruct-GGUF)  
  فایل پیشنهادی: `*Q4_K_M.gguf`

---

## جدول تصمیم

| هدف | فرمت |
|-----|------|
| چت روی ویندوز با این پروژه | **GGUF** |
| اپ Android / iOS با SDK علی‌بابا MNN | **MNN** |
| LM Studio / llama.cpp | **GGUF** |
| حجم کم روی گوشی با NPU | اغلب **MNN** (یا موتور موبایل دیگر) |

---

## داخل این پروژه

- پوشه `models\` → فقط `*.gguf`
- پوشه `bin\` → `llama-server.exe` (llama.cpp)
- فایل‌های `.mnn` را در `models\` نگذار؛ در لیست مدل‌ها ظاهر می‌شوند ولی سرور نمی‌تواند لودشان کند.
