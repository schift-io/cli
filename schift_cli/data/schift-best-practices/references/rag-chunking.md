---
title: Let Schift Handle Chunking via Bucket Upload
impact: HIGH
impactDescription: Custom chunking loses document structure (headings, tables, lists), produces uneven chunk quality, and requires maintaining your own chunking logic. Schift's bucket upload handles OCR, structure-aware chunking, and embedding automatically.
tags:
  - rag
  - chunking
  - bucket
  - document-structure
  - preprocessing
---

## Let Schift Handle Chunking via Bucket Upload

Chunking is one of the most impactful and underestimated decisions in a RAG pipeline. Naively splitting text by character count or regex destroys semantic units: headings get separated from their content, table rows become orphaned fragments, and list items lose their parent context. The result is chunks that embed poorly and retrieve incorrectly.

Schift's bucket upload pipeline runs document parsing, OCR, and structure-aware chunking on your behalf. It understands heading hierarchies, tables, code blocks, and lists — producing semantically coherent chunks that embed and retrieve at higher quality without any custom code.

### Incorrect

Custom regex or fixed-size chunking that destroys document structure:

```python
# Python — naive fixed-size chunking, loses all structure
import re
from schift import Schift

client = Schift(api_key="sch_...")

with open("technical_report.pdf", "rb") as f:
    raw_text = extract_text_from_pdf(f)  # flat string, all structure lost

# Split every 500 characters regardless of sentence or section boundaries
chunks = [raw_text[i:i+500] for i in range(0, len(raw_text), 500)]

# Problems:
# - Heading "## Performance Results" ends up in a different chunk than the table below it
# - Table rows split mid-row: "| 98.2% | la" / "tency 12ms |"
# - Code blocks broken at arbitrary positions
# - No metadata: no page number, no section, no source

for i, chunk in enumerate(chunks):
    client.embed_and_insert(collection_id, chunk, metadata={"index": i})
```

```typescript
// TypeScript — naive regex split, loses paragraph context
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

const rawText = await extractText('technical_report.pdf');  // flat string

// Split on double newlines — misses tables, code blocks, lists
const chunks = rawText.split(/\n\n+/).filter(c => c.trim().length > 0);

// No overlap, no metadata, no awareness of document hierarchy
for (const chunk of chunks) {
  await client.embedAndInsert(collectionId, chunk);
}
```

This approach drops all structural signals that models rely on to understand context. A chunk reading `"98.2%  12ms  4.1GB"` is meaningless without the table header that provides column names.

### Correct

Upload directly to a Schift bucket and let the pipeline handle chunking:

```python
# Python — bucket upload: structure-aware chunking, no manual work
from schift import Schift

client = Schift(api_key="sch_...")

# Upload the raw file — Schift handles OCR, parsing, chunking, embedding
with open("technical_report.pdf", "rb") as f:
    result = client.bucket.upload(
        bucket_id=bucket_id,
        file=f,
        filename="technical_report.pdf",
        metadata={
            "source": "internal-research",
            "version": "2026-Q1",
            "department": "engineering",
        }
    )

print(result.chunk_count)   # e.g. 142 semantically coherent chunks
print(result.document_id)   # reference for deletion or re-indexing

# Schift preserves:
# - Heading hierarchy (H1 > H2 > H3 as metadata fields)
# - Table structure (header row context attached to each data row chunk)
# - Code blocks (kept intact, tagged as code)
# - List items (grouped under their parent heading)
```

```typescript
// TypeScript — bucket upload: let Schift do the heavy lifting
import { Schift } from '@schift-io/sdk';
import { readFileSync } from 'fs';

const client = new Schift({ apiKey: 'sch_...' });

const fileBuffer = readFileSync('technical_report.pdf');

const result = await client.bucket.upload(bucketId, fileBuffer, {
  filename: 'technical_report.pdf',
  metadata: {
    source: 'internal-research',
    version: '2026-Q1',
    department: 'engineering',
  },
});

console.log(result.chunkCount);   // semantically coherent chunks
console.log(result.documentId);   // for future reference or deletion
```

If you must chunk manually (e.g., streaming data with no file format), follow these rules:

```python
# Python — manual chunking fallback: overlap + boundaries + metadata
def chunk_text_safely(text: str, source: str, page: int = 0) -> list[dict]:
    paragraphs = text.split("\n\n")
    chunks = []
    window = []
    window_size = 0
    target_size = 400   # tokens (approximate)
    overlap_size = 60   # 10–20% overlap to preserve cross-boundary context

    for para in paragraphs:
        words = para.split()
        window.extend(words)
        window_size += len(words)

        if window_size >= target_size:
            chunk_text = " ".join(window)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": source,
                    "page": page,
                    "char_count": len(chunk_text),
                }
            })
            # Retain overlap to preserve context across chunk boundary
            window = window[-overlap_size:]
            window_size = len(window)

    if window:  # flush remainder
        chunks.append({
            "text": " ".join(window),
            "metadata": {"source": source, "page": page}
        })

    return chunks
```

**Manual chunking checklist (if unavoidable):**

| Rule | Why |
|------|-----|
| 10–20% overlap between chunks | Prevents context loss at boundaries |
| Respect paragraph/sentence boundaries | Keeps semantic units intact |
| Include source, page, section in metadata | Enables filtered search and attribution |
| Target 300–500 tokens per chunk | Balances precision and recall |
| Never split mid-sentence | Broken sentences embed poorly |

## Reference

- https://docs.schift.io/buckets/upload
- https://docs.schift.io/buckets/chunking
