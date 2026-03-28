---
title: Bucket Upload for Document Ingestion
impact: HIGH
impactDescription: Manual chunking and embedding pipelines are error-prone and skip OCR, layout parsing, and deduplication that the bucket pipeline performs automatically. Using bucket.upload() reduces ingestion code from ~50 lines to 2.
tags: [bucket, upload, ingestion, ocr, chunking, pdf, docx]
---

## Use bucket.upload() for Document Ingestion

Schift buckets provide a fully managed ingestion pipeline: upload raw files and the bucket handles OCR, chunking, embedding, and FAISS index updates automatically. Building this pipeline manually duplicates work the platform already does and introduces subtle inconsistencies (chunk overlap, encoding issues, missed page breaks).

Supported formats: **PDF, DOCX, TXT, MD**, and images (PNG, JPG, WEBP) with automatic OCR.

### Incorrect

```python
# Python - manual pipeline: reads file, chunks, embeds, adds to collection
import os
from schift import Schift

client = Schift()

def ingest_pdf(file_path: str, collection_id: str):
    # Step 1: extract text manually (no layout awareness, no OCR for scanned pages)
    import PyPDF2
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        full_text = " ".join(page.extract_text() for page in reader.pages)

    # Step 2: chunk manually (naive split, loses sentence boundaries)
    chunk_size = 500
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]

    # Step 3: embed each chunk (no deduplication, no credit hold)
    embeddings = client.embed_batch(chunks)

    # Step 4: add to collection (separate API call per chunk batch)
    for chunk, embedding in zip(chunks, embeddings.vectors):
        client.collection.add(collection_id, text=chunk, vector=embedding)
```

```typescript
// TypeScript - same manual approach
import { Schift } from '@schift-io/sdk';
import * as fs from 'fs';

const client = new Schift();

async function ingestPdf(filePath: string, collectionId: string) {
  // manual extraction, chunking, embedding, and indexing
  const text = extractTextFromPdf(filePath);              // not shown, error-prone
  const chunks = splitIntoChunks(text, 500);              // naive chunker
  const embeddings = await client.embedBatch(chunks);
  for (const [chunk, vec] of zip(chunks, embeddings.vectors)) {
    await client.collection.add(collectionId, { text: chunk, vector: vec });
  }
}
```

This approach misses scanned-page OCR, skips layout heuristics (headers, tables, footnotes), does no deduplication on re-upload, and requires maintaining the chunking logic yourself.

### Correct

```python
# Python - bucket.upload() handles the entire pipeline
import os
from schift import Schift

client = Schift()

# Create the bucket once (idempotent name)
bucket = client.bucket.create("legal-contracts")

# Upload one or many files; returns immediately with a job ID
job = client.bucket.upload(
    bucket.id,
    files=["contracts/acme_2026.pdf", "contracts/globex_2026.pdf"]
)

# Optional: poll until ingestion completes before searching
job.wait()  # blocks until all files are indexed

# Search across all uploaded documents
results = client.bucket.search(bucket.id, "indemnification clause")
for r in results.hits:
    print(r.text, r.score)
```

```typescript
// TypeScript - same two-step pattern
import { Schift } from '@schift-io/sdk';
import * as fs from 'fs';

const client = new Schift();

const bucket = await client.bucket.create('legal-contracts');

const job = await client.bucket.upload(bucket.id, {
  files: ['contracts/acme_2026.pdf', 'contracts/globex_2026.pdf'],
});

await job.wait(); // optional: wait for indexing to complete

const results = await client.bucket.search(bucket.id, 'indemnification clause');
results.hits.forEach(r => console.log(r.text, r.score));
```

**Credit hold pattern**: `bucket.upload()` pre-deducts an estimated token cost at upload time (a hold), then refunds the difference once actual usage is measured. You are never charged more than the hold amount. This prevents quota overruns during large uploads.

**Re-upload deduplication**: Uploading the same file content twice to the same bucket is a no-op — Schift detects the content hash and skips re-embedding.

## Reference

- https://docs.schift.io/buckets/upload
- https://docs.schift.io/buckets/supported-formats
- https://docs.schift.io/billing/credit-hold
