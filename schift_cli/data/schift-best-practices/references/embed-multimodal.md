---
title: Use modality parameter for non-text inputs
impact: CRITICAL
impactDescription: Passing raw image bytes or file content as a plain text string produces garbage embeddings. The modality parameter routes the input through the correct encoder before projection into canonical space.
tags: [embedding, multimodal, image, document, audio]
---

## Use modality parameter for non-text inputs

Schift supports five modalities: `text`, `image`, `audio`, `video`, and `document`. Every modality is projected into the same canonical 1024-dimensional space, so cross-modal search (e.g. text query against image collection) works out of the box — but only if you specify the correct `modality` when embedding.

Passing raw binary content without setting `modality` causes Schift to treat the input as UTF-8 text, producing meaningless embeddings.

**Incorrect** — passing image bytes as plain text produces garbage vectors:

```python
# Python - DON'T do this
from schift import Schift

client = Schift(api_key="sch_...")

with open("photo.jpg", "rb") as f:
    image_bytes = f.read()

# Wrong: embed() with no modality treats input as text
result = client.embed(image_bytes)   # garbage embedding
```

```typescript
// TypeScript - DON'T do this
import { Schift } from '@schift-io/sdk';
import { readFileSync } from 'fs';

const client = new Schift({ apiKey: 'sch_...' });

const imageBuffer = readFileSync('photo.jpg');

// Wrong: no modality — treated as text
const result = await client.embed(imageBuffer.toString());  // garbage embedding
```

**Correct** — specify `modality="image"` (or the appropriate modality) and pass the file path or bytes:

```python
# Python - DO this
from schift import Schift

client = Schift(api_key="sch_...")

# Embed a single image
result = client.embed("photo.jpg", modality="image")
image_vector = result.embedding   # 1024d, same space as text embeddings

# Embed a PDF document
doc_result = client.embed("report.pdf", modality="document")

# Cross-modal search: text query against image collection
text_query = client.embed("a golden retriever running in a park", modality="text")
# text_query.embedding can now be used to search an image collection directly

# Batch embed multiple images
image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
results = client.embed_batch(image_paths, modality="image")
vectors = [r.embedding for r in results]
```

```typescript
// TypeScript - DO this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Embed a single image by file path
const result = await client.embed('photo.jpg', { modality: 'image' });
const imageVector = result.embedding;   // 1024d, same space as text

// Embed a PDF document
const docResult = await client.embed('report.pdf', { modality: 'document' });

// Cross-modal: text query against image collection
const textQuery = await client.embed(
  'a golden retriever running in a park',
  { modality: 'text' },
);
// textQuery.embedding searches image collections directly

// Batch embed multiple images
const imagePaths = ['img1.jpg', 'img2.jpg', 'img3.jpg'];
const results = await client.embedBatch(imagePaths, { modality: 'image' });
const vectors = results.map((r) => r.embedding);
```

Because all modalities share the same canonical 1024d space, you can search across modalities without any additional conversion step. A text embedding and an image embedding are directly comparable with cosine similarity.

Supported modality values: `text` (default), `image`, `audio`, `video`, `document`.

## Reference

- https://docs.schift.io/api/embed#modality
- https://docs.schift.io/concepts/canonical-space
