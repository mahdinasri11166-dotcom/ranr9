# برنامه‌نویسی و خروجی فایل

**مهدی طریری** — mahditariri@gmail.com

با **حالت Agent** مدل می‌تواند فایل کد واقعی در `workspace\` بسازد.

## ابزارها

| ابزار | کار |
|--------|-----|
| `write_code` | یک فایل کد با پسوند مناسب |
| `write_file` | هر فایل متنی |
| `scaffold_project` | چند فایل یکجا (پروژه) |
| `make_zip` | بسته‌بندی zip |
| `run_python` | اجرای پایتون در workspace |
| `list_code_formats` | لیست پسوندها/زبان‌ها |

## فرمت‌های پشتیبانی‌شده (نمونه)

`py js ts tsx jsx html css scss json yaml md c cpp h cs java go rs php rb sql sh bat ps1 xml vue svelte ...`

## مثال درخواست به مدل

- «یک API فلسک در workspace بنویس»
- «پروژه HTML/CSS/JS صفحه فرود بساز و zip کن»
- «اسکریپت پایتون تبدیل CSV بساز و اجرا کن»

خروجی‌ها داخل پوشه **`workspace\`** ذخیره می‌شوند.
