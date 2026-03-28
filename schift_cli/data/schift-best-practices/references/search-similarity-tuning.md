---
title: Tune top_k and Similarity Threshold for Your Use Case
impact: CRITICAL
impactDescription: Using wrong top_k or no score threshold causes either noisy results (too many irrelevant chunks passed to LLM) or missed relevant results, directly degrading answer quality and wasting tokens.
tags:
  - search
  - retrieval
  - top_k
  - score_threshold
  - precision
  - recall
---

## Tune top_k and Similarity Threshold for Your Use Case

The default `top_k=10` is a reasonable starting point but rarely optimal. Every use case has a different precision/recall trade-off: a chatbot answering factual questions needs tight, high-confidence results, while a research tool benefits from broader recall. Passing too many low-quality chunks to an LLM inflates costs and degrades answer quality; returning too few misses the relevant context entirely.

Use `score_threshold` to discard results below a minimum similarity score. Schift returns cosine similarity scores in `[0, 1]` — results below ~0.65 are typically noise.

### Incorrect

Using default `top_k=10` everywhere with no threshold filter:

```python
# Python — no threshold, fixed top_k for all use cases
from schift import Schift

client = Schift(api_key="sch_...")

# Same settings for everything: chatbot QA, exploratory search, code lookup
results = client.search(collection_id, query)  # top_k defaults to 10, no threshold

for r in results:
    context += r.text  # may include chunks with score=0.42 (largely irrelevant)
```

```typescript
// TypeScript — no threshold, fixed top_k for all use cases
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Same settings for everything
const results = await client.search(collectionId, query);  // top_k=10, no threshold

const context = results.map(r => r.text).join('\n');  // includes noise
```

This passes irrelevant chunks to the LLM, increases prompt token count, and produces hallucinated or unfocused answers.

### Correct

Set `top_k` and `score_threshold` based on the retrieval goal:

```python
# Python — tuned per use case
from schift import Schift

client = Schift(api_key="sch_...")

# Chatbot Q&A: tight precision, high confidence
qa_results = client.search(
    collection_id,
    query,
    top_k=3,            # few but precise chunks
    score_threshold=0.78  # discard anything below 78% similarity
)

# Research / exploratory: wider recall, lower threshold
explore_results = client.search(
    collection_id,
    query,
    top_k=30,           # broad recall for exploration
    score_threshold=0.55  # accept weaker matches
)

# Code retrieval: moderate, function-level precision
code_results = client.search(
    collection_id,
    query,
    top_k=5,
    score_threshold=0.70
)

# Always check: if nothing passes threshold, surface a "no results" message
if not qa_results:
    return "I couldn't find relevant information for your question."
```

```typescript
// TypeScript — tuned per use case
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Chatbot Q&A: tight precision, high confidence
const qaResults = await client.search(collectionId, query, {
  topK: 3,
  scoreThreshold: 0.78,
});

// Research / exploratory: wider recall
const exploreResults = await client.search(collectionId, query, {
  topK: 30,
  scoreThreshold: 0.55,
});

// Code retrieval
const codeResults = await client.search(collectionId, query, {
  topK: 5,
  scoreThreshold: 0.70,
});

// Handle empty results gracefully
if (qaResults.length === 0) {
  return "I couldn't find relevant information for your question.";
}
```

**Rule of thumb by use case:**

| Use Case | top_k | score_threshold |
|----------|-------|-----------------|
| Chatbot Q&A | 3–5 | 0.75–0.82 |
| Document Q&A (long docs) | 5–8 | 0.70–0.78 |
| Code retrieval | 3–6 | 0.68–0.75 |
| Research / exploration | 20–50 | 0.50–0.62 |
| Fact verification | 1–3 | 0.80–0.88 |

Start with these ranges and adjust based on observed result quality. Log score distributions during development to calibrate thresholds for your data.

## Reference

- https://docs.schift.io/search/parameters
