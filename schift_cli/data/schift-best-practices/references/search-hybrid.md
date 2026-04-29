---
title: Combine Semantic Search with Metadata Filters for Precise Retrieval
impact: HIGH
impactDescription: Pure semantic search returns results that are thematically similar but contextually wrong — e.g., querying "quarterly revenue" returns documents from the wrong year or department. Adding metadata filters eliminates these false positives without sacrificing semantic ranking quality.
tags:
  - search
  - filters
  - metadata
  - hybrid-search
  - retrieval
---

## Combine Semantic Search with Metadata Filters for Precise Retrieval

Semantic search ranks results by vector similarity, which captures meaning well but is blind to structured attributes like dates, departments, document types, or user ownership. Without filters, a query for "quarterly revenue" might surface a 2019 report with slightly higher similarity than the 2025 report you actually need.

The `filter` parameter in collection-scoped search applies exact-match or range constraints on document metadata before semantic ranking. The semantic model then ranks only the pre-filtered candidates, giving you both precision and relevance.

### Incorrect

Pure semantic search without filters returns semantically similar but contextually irrelevant results:

```python
# Python — semantic-only search, no filters
from schift import Schift

client = Schift(api_key="sch_...")

# Searching for 2025 finance data — but will return results from any year/department
results = client.query(
    "quarterly revenue growth",
    collection="finance-reports",
    top_k=5,
)

# Results may include 2019 marketing reports that mention "revenue" prominently
for r in results:
    print(r.text, r.score)
```

```typescript
// TypeScript — semantic-only search, no filters
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// No filters — returns semantically similar but potentially wrong-year docs
const results = await client.search({
  collection: 'finance-reports',
  query: 'quarterly revenue growth',
  topK: 5,
});
```

This wastes top_k slots on irrelevant documents and requires the LLM to reason about document provenance instead of just answering.

### Correct

Use the `filter` parameter to narrow candidates by metadata before semantic ranking:

```python
# Python — hybrid search with metadata filters
from schift import Schift

client = Schift(api_key="sch_...")

# Narrow to 2025 finance department docs, then rank by semantic similarity
results = client.query(
    "quarterly revenue growth",
    collection="finance-reports",
    top_k=5,
)

# All results are from the right context; semantic score reflects true relevance
for r in results:
    print(r.metadata["year"], r.metadata["department"], r.score, r.text[:100])


# Multi-value filter: search across multiple years
results = client.query(
    "revenue trend analysis",
    collection="finance-reports",
    top_k=10,
)

# Filter by recency for support tickets
recent_tickets = client.query(
    "payment gateway timeout error",
    collection="support-tickets",
    top_k=8,
)
```

```typescript
// TypeScript — hybrid search with metadata filters
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Narrow to 2025 finance docs, then semantic ranking
const results = await client.search({
  collection: 'finance-reports',
  query: 'quarterly revenue growth',
  topK: 5,
  filter: {
    year: 2025,
    department: 'finance',
  },
  mode: 'hybrid',
});

results.forEach(r => {
  console.log(r.metadata.year, r.metadata.department, r.score, r.text.slice(0, 100));
});

// Multi-value filter across years
const trendResults = await client.search({
  collection: 'finance-reports',
  query: 'revenue trend analysis',
  topK: 10,
  filter: {
    year: { $in: [2023, 2024, 2025] },
    department: 'finance',
    doc_type: 'quarterly-report',
  },
  mode: 'hybrid',
});

// Filter for recent high-priority support tickets
const recentTickets = await client.search({
  collection: 'support-tickets',
  query: 'payment gateway timeout error',
  topK: 8,
  filter: {
    status: 'open',
    created_after: '2026-01-01',
    priority: { $in: ['high', 'critical'] },
  },
  mode: 'hybrid',
});
```

**Supported filter operators:**

| Operator | Meaning | Example |
|----------|---------|---------|
| exact match | `field: value` | `"year": 2025` |
| `$in` | any of these values | `"status": { "$in": ["open", "pending"] }` |
| `$gt` / `$gte` | greater than | `"score": { "$gte": 90 }` |
| `$lt` / `$lte` | less than | `"created_at": { "$lt": "2025-06-01" }` |

Define filterable fields in your collection schema at creation time — only schema-declared fields are indexed for filtering.

## Reference

- https://docs.schift.io/search/filters
