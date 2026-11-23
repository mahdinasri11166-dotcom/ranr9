# بهینه‌سازی RAG با Embedding

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## معماری

```
متن کتاب/چت → Chunking → Embedding (MiniLM چندزبانه)
    → FAISS IndexFlatIP (cosine با بردار نرمال)
    → بازیابی top fetch_k
    → فیلتر min_score + امتیاز کلمه کلیدی
    → MMR برای تنوع
    → محدودیت max_inject_chars
    → تزریق به system prompt مدل
```

## مدل Embedding

پیش‌فرض:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

- مناسب فارسی و انگلیسی
- ابعاد 384
- نسبتاً سبک برای CPU

تنظیم در: `memory/vectors/rag_config.json` یا API `POST /config`

## پارامترهای مهم (rag_config.json)

| کلید | پیش‌فرض | معنی |
|------|---------|------|
| chunk_size | 420 | طول تقریبی هر تکه |
| chunk_overlap | 90 | همپوشانی تکه‌ها |
| top_k | 5 | تعداد نهایی نتایج |
| fetch_k | 24 | کاندیداهای اولیه از FAISS |
| min_score | 0.25 | حداقل شباهت |
| use_mmr | true | تنوع نتایج |
| mmr_lambda | 0.7 | تعادل ارتباط/تنوع |
| keyword_weight | 0.06 | وزن تطبیق کلمه کلیدی |
| max_inject_chars | 3500 | سقف متن تزریقی به مدل |

## اجرا

```bat
cd scripts\python
pip install -r requirements.txt
python memory_server.py
```

ورود دسته‌ای کتاب‌ها و حافظه متنی:

```bat
python ingest_books.py
```

(سرور باید روی 8765 روشن باشد)

## API

- `POST /ingest` `{ "text", "source", "id?" }`
- `POST /search` `{ "query", "top_k?", "source?", "min_score?", "use_mmr?" }`
- `GET /config` / `POST /config`
- `GET /health` / `GET /list`
- `DELETE /item/<id>` / `POST /clear`

## نکات کیفیت

1. کتاب‌ها را فصل‌بندی کنید، نه یک فایل چند مگابایتی خام.
2. بعد از اضافه کردن متن، دوباره search را تست کنید.
3. اگر نتایج نامرتبط است `min_score` را بالا ببرید (مثلا 0.35).
4. اگر نتایج تکراری است MMR را روشن نگه دارید.
5. برای دامنه خیلی تخصصی، بعداً می‌توان مدل embedding دامنه‌ای fine-tune کرد.

## محدودیت

- کیفیت RAG به کیفیت chunk و embedding وابسته است، نه به «یادگیری وزن LLM».
- اولین بار دانلود مدل embedding از اینترنت لازم است.


See also: docs/RERANKER.md
