---
title: Use embed_batch() for multiple texts
impact: CRITICAL
impactDescription: Looping embed() one-by-one produces 10-50x more API calls than a single embed_batch() call, increasing latency and cost proportionally.
tags: [embedding, performance, cost, batch]
---

## Use embed_batch() for multiple texts

When embedding more than one piece of text, always use `embed_batch()` instead of calling `embed()` in a loop. Each `embed()` call is a separate HTTP round-trip. `embed_batch()` sends all texts in a single request (up to 100 per call) and returns embeddings in the same order.

**Incorrect** — calling `embed()` in a loop creates one HTTP request per text:

```python
# Python - DON'T do this
from schift import Schift

client = Schift(api_key="sch_...")
texts = ["cat", "dog", "bird", "fish"]

embeddings = []
for text in texts:
    result = client.embed(text)       # 4 separate API calls
    embeddings.append(result.embedding)
```

```typescript
// TypeScript - DON'T do this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });
const texts = ['cat', 'dog', 'bird', 'fish'];

const embeddings = [];
for (const text of texts) {
  const result = await client.embed(text);   // 4 separate API calls
  embeddings.push(result.embedding);
}
```

**Correct** — one `embed_batch()` call handles the entire list:

```python
# Python - DO this
from schift import Schift

client = Schift(api_key="sch_...")
texts = ["cat", "dog", "bird", "fish"]

results = client.embed_batch(texts)           # 1 API call
embeddings = [r.embedding for r in results]  # same order as input

# For large datasets, chunk into batches of up to 100
BATCH_SIZE = 100
all_embeddings = []
for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i : i + BATCH_SIZE]
    results = client.embed_batch(batch)
    all_embeddings.extend(r.embedding for r in results)
```

```typescript
// TypeScript - DO this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });
const texts = ['cat', 'dog', 'bird', 'fish'];

const results = await client.embedBatch(texts);         // 1 API call
const embeddings = results.map((r) => r.embedding);     // same order as input

// For large datasets, chunk into batches of up to 100
const BATCH_SIZE = 100;
const allEmbeddings: number[][] = [];
for (let i = 0; i < texts.length; i += BATCH_SIZE) {
  const batch = texts.slice(i, i + BATCH_SIZE);
  const batchResults = await client.embedBatch(batch);
  allEmbeddings.push(...batchResults.map((r) => r.embedding));
}
```

The `embed_batch()` / `embedBatch()` limit is 100 texts per call. For larger datasets, split into chunks of 100 as shown above. Results are always returned in the same order as the input list.

## Reference

- https://docs.schift.io/api/embed#batch
