# Reranker برای دقت بالاتر RAG

**توسعه‌دهنده:** مهدی طریری — mahditariri@gmail.com

## چرا Reranker؟

Embedding (bi-encoder) سریع است ولی دقت جفت «سؤال–متن» متوسط است.  
**Cross-Encoder Reranker** هر کاندیدا را همراه با خود سؤال امتیاز می‌دهد و معمولاً دقت بالاتری می‌دهد.

## خط لوله

1. Embedding retrieval از FAISS (`fetch_k` کاندیدا)
2. فیلتر اولیه + keyword bonus
3. **Cross-Encoder rerank** روی `rerank_candidates`
4. فیلتر `min_rerank_score`
5. MMR (تنوع)
6. محدودیت طول تزریق به مدل

## مدل پیش‌فرض

`cross-encoder/ms-marco-MiniLM-L-6-v2`

سبک و مناسب CPU. برای کیفیت بیشتر (و کندتر):

- `cross-encoder/ms-marco-MiniLM-L-12-v2`
- `BAAI/bge-reranker-base`
- `BAAI/bge-reranker-v2-m3` (چندزبانه قوی‌تر، سنگین‌تر)

در `memory/vectors/rag_config.json`:

```json
{
  "use_reranker": true,
  "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "rerank_candidates": 20,
  "min_rerank_score": -5.0
}
```

یا با API:

```text
POST http://127.0.0.1:8765/config
{"use_reranker": true, "reranker_model": "BAAI/bge-reranker-base"}
```

برای یک جستجو بدون ریرنکر:

```text
POST /search
{"query": "...", "use_reranker": false}
```

## نکته عملکرد

اولین درخواست ریرنکر مدل را از اینترنت/کش لود می‌کند و ممکن است چند ثانیه طول بکشد.  
روی CPU برای `rerank_candidates=20` معمولاً قابل قبول است.

## وابستگی

همان `sentence-transformers` (کلاس `CrossEncoder`).
