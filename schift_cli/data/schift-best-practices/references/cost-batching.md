---
title: Batch API Calls to Minimize Per-Call Overhead and Cost
impact: MEDIUM
impactDescription: Each individual API call is billed as 1 unit regardless of how many texts it contains (up to 100). Sending 1000 single-text calls costs 100x more than sending 10 batches of 100 texts. Batching is the single highest-leverage cost optimization.
tags:
  - cost
  - batching
  - embed
  - performance
  - throughput
---

## Batch API Calls to Minimize Per-Call Overhead and Cost

Schift billing is per API call, not per text. One call can embed up to 100 texts — and it costs exactly the same as one call embedding a single text. This means that how you structure your calls matters far more than how much text you send.

The rule is simple: never make one API call per document. Always accumulate texts into batches of up to 100 and call `embed_batch` / `embedBatch` once per batch.

**Billing unit**: 1 API call = 1 billing unit = $0.10 per 1,000 calls, regardless of batch size (up to 100 items per call).

### Incorrect

One embed call per text — 1000 texts = 1000 API calls = $0.10:

```python
# Python — one call per document: 1000 texts = 1000 API calls = $0.10
from schift import Schift

client = Schift(api_key="sch_...")

documents = load_documents()  # 1000 documents

# Every call is 1 billing unit — this is 1000 billing units
for doc in documents:
    embedding = client.embed(doc.text)  # 1 call per doc
    store_embedding(doc.id, embedding)

# Cost: 1000 calls × ($0.10 / 1000 calls) = $0.10
# Latency: 1000 sequential round trips (or N parallel, but N connections)
```

```typescript
// TypeScript — same problem: one call per document
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

const documents = await loadDocuments();  // 1000 documents

// Sequential: slow and wasteful
for (const doc of documents) {
  const embedding = await client.embed(doc.text);  // 1 billing unit each
  await storeEmbedding(doc.id, embedding);
}

// Even with Promise.all, still 1000 separate API calls:
const embeddings = await Promise.all(
  documents.map(doc => client.embed(doc.text))  // still 1000 calls
);
// Cost: 1000 billing units = $0.10
```

### Correct

Batch up to 100 texts per call — 1000 texts = 10 API calls = $0.001:

```python
# Python — batch embedding: 1000 texts in 10 calls = 10 billing units = $0.001
from schift import Schift

client = Schift(api_key="sch_...")

documents = load_documents()  # 1000 documents
BATCH_SIZE = 100  # max 100 per call

# Chunk documents into batches of 100
batches = [documents[i:i+BATCH_SIZE] for i in range(0, len(documents), BATCH_SIZE)]

for batch in batches:
    texts = [doc.text for doc in batch]
    embeddings = client.embed_batch(texts)  # 1 call for up to 100 texts

    for doc, embedding in zip(batch, embeddings):
        store_embedding(doc.id, embedding)

# Cost: 10 calls × ($0.10 / 1000 calls) = $0.001  (100x cheaper)
# Throughput: 10 round trips vs 1000
```

```typescript
// TypeScript — batch embedding: 100x cost reduction
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

const documents = await loadDocuments();  // 1000 documents
const BATCH_SIZE = 100;

// Helper: split array into chunks
function chunk<T>(arr: T[], size: number): T[][] {
  return Array.from({ length: Math.ceil(arr.length / size) }, (_, i) =>
    arr.slice(i * size, i * size + size)
  );
}

const batches = chunk(documents, BATCH_SIZE);

for (const batch of batches) {
  const texts = batch.map(doc => doc.text);
  const embeddings = await client.embedBatch(texts);  // 1 call for up to 100 texts

  await Promise.all(
    batch.map((doc, i) => storeEmbedding(doc.id, embeddings[i]))
  );
}

// Cost: 10 billing units = $0.001  (vs $0.10 for individual calls)
```

**Cost comparison at scale:**

| Approach | 1K texts | 10K texts | 100K texts |
|----------|----------|-----------|------------|
| 1 call per text | $0.10 | $1.00 | $10.00 |
| Batch of 100 | $0.001 | $0.01 | $0.10 |
| **Savings** | **99%** | **99%** | **99%** |

Also cache embeddings client-side for repeated queries to avoid redundant API calls entirely:

```python
# Python — client-side embedding cache for repeated queries
import hashlib
from functools import lru_cache
from schift import Schift

client = Schift(api_key="sch_...")

# Simple in-memory cache (use Redis or a file cache for persistence)
_embedding_cache: dict[str, list[float]] = {}

def embed_with_cache(text: str) -> list[float]:
    key = hashlib.sha256(text.encode()).hexdigest()
    if key not in _embedding_cache:
        _embedding_cache[key] = client.embed(text)
    return _embedding_cache[key]

# For search queries that repeat across users (e.g., "what is your refund policy?"),
# this means the embedding is computed once and reused for all matching queries.
```

```typescript
// TypeScript — client-side embedding cache
import { createHash } from 'crypto';
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });
const cache = new Map<string, number[]>();

async function embedWithCache(text: string): Promise<number[]> {
  const key = createHash('sha256').update(text).digest('hex');
  if (!cache.has(key)) {
    cache.set(key, await client.embed(text));
  }
  return cache.get(key)!;
}
// Use a TTL cache (e.g., lru-cache with maxAge) for production.
```

**Batching checklist:**

- Use `embed_batch` / `embedBatch` for all bulk operations (indexing, re-indexing, data migration)
- Use `embed` only for single real-time queries (user search input)
- Cache query embeddings when the same query may repeat (chatbot, search UI)
- For very large datasets (>100K texts), process batches concurrently with a concurrency limit of 5–10

## Reference

- https://docs.schift.io/api/embed-batch
- https://docs.schift.io/pricing
