---
title: Design Collections by Domain/Use-Case, Not by Data Source
impact: HIGH
impactDescription: A single monolithic collection forces every query to search irrelevant data, bloating latency and degrading result quality. Per-file collections create management overhead and prevent cross-document ranking within a domain. Domain-aligned collections with consistent metadata schemas give you both search quality and operational simplicity.
tags:
  - collection
  - schema
  - design
  - organization
  - metadata
---

## Design Collections by Domain/Use-Case, Not by Data Source

Collection design is a structural decision that affects search quality, filter performance, and long-term maintainability. The two common anti-patterns are opposites of each other: one giant collection that holds everything (poor signal-to-noise ratio per query), and one collection per uploaded file (combinatorial overhead, no cross-document ranking).

The correct approach is to group documents by the queries they serve. A user asking "how do I reset my API key?" should search `support-docs` — not wade through API reference and release notes in the same index.

### Incorrect

**Anti-pattern A: One monolithic collection**

```python
# Python — everything in one collection
from schift import Schift

client = Schift(api_key="sch_...")

# Dumping all company knowledge into a single collection
client.collection.add("everything", documents=[
    {"id": "pd-001", "text": "Product feature: drag-and-drop upload..."},
    {"id": "st-001", "text": "Support ticket: user cannot login..."},
    {"id": "api-001", "text": "POST /v1/embed — Creates embeddings..."},
    {"id": "rn-001", "text": "Release notes v2.3: added batch support..."},
])

# Query now competes against all domains — noisy results
results = client.query("how to embed documents", collection="everything")
# Returns: API reference, support tickets, release notes, all mixed together
```

**Anti-pattern B: One collection per file**

```python
# Python — a new collection for every uploaded file
for filename, content in uploaded_files:
    collection_id = filename.replace(".pdf", "").replace(" ", "-")
    client.collection.create(collection_id, schema={})  # no schema
    client.collection.add(collection_id, documents=[{"id": "doc", "text": content}])

# Now you must search 200 collections separately — impossible to rank across files
```

```typescript
// TypeScript — same anti-patterns
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Anti-pattern A: monolithic
await client.collection.add('everything', { documents: allMyDocuments });

// Anti-pattern B: per-file
for (const file of uploadedFiles) {
  const id = file.name.replace('.pdf', '');
  await client.collection.create(id, { schema: {} });  // no schema
  await client.collection.add(id, { documents: [{ id: 'doc', text: file.content }] });
}
```

### Correct

Create collections per domain/use-case with a defined metadata schema:

```python
# Python — domain-aligned collections with schemas
from schift import Schift

client = Schift(api_key="sch_...")

# Define schema for each domain at creation — only these fields are filter-indexed
client.collection.create("product-docs", schema={
    "fields": {
        "version":    {"type": "string",  "filterable": True},
        "category":   {"type": "string",  "filterable": True},  # "feature", "guide", "faq"
        "updated_at": {"type": "date",    "filterable": True},
        "language":   {"type": "string",  "filterable": True},
    }
})

client.collection.create("support-tickets", schema={
    "fields": {
        "status":       {"type": "string",  "filterable": True},  # "open", "closed"
        "priority":     {"type": "string",  "filterable": True},
        "created_at":   {"type": "date",    "filterable": True},
        "product_area": {"type": "string",  "filterable": True},
    }
})

client.collection.create("api-reference", schema={
    "fields": {
        "endpoint":    {"type": "string",  "filterable": True},
        "method":      {"type": "string",  "filterable": True},  # "GET", "POST", etc.
        "version":     {"type": "string",  "filterable": True},
        "deprecated":  {"type": "boolean", "filterable": True},
    }
})

# Ingest respects the schema — metadata is validated at write time
client.collection.add("product-docs", documents=[
    {
        "id": "pd-drag-drop-001",
        "text": "Drag-and-drop upload lets you add files directly to a bucket...",
        "metadata": {
            "version": "2.3",
            "category": "feature",
            "updated_at": "2026-02-10",
            "language": "en",
        }
    },
])

# Queries are scoped to the right domain — clean, relevant results
product_results = client.query(
    "how to upload files",
    collection="product-docs",
    top_k=5,
)

support_results = client.query(
    "upload fails with 413 error",
    collection="support-tickets",
    top_k=8,
)

api_results = client.query(
    "create embedding endpoint",
    collection="api-reference",
    top_k=3,
)
```

```typescript
// TypeScript — domain-aligned collections with schemas
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Create collections with explicit schemas
await client.collection.create('product-docs', {
  schema: {
    fields: {
      version:    { type: 'string',  filterable: true },
      category:   { type: 'string',  filterable: true },
      updated_at: { type: 'date',    filterable: true },
      language:   { type: 'string',  filterable: true },
    },
  },
});

await client.collection.create('support-tickets', {
  schema: {
    fields: {
      status:       { type: 'string',  filterable: true },
      priority:     { type: 'string',  filterable: true },
      created_at:   { type: 'date',    filterable: true },
      product_area: { type: 'string',  filterable: true },
    },
  },
});

await client.collection.create('api-reference', {
  schema: {
    fields: {
      endpoint:   { type: 'string',  filterable: true },
      method:     { type: 'string',  filterable: true },
      version:    { type: 'string',  filterable: true },
      deprecated: { type: 'boolean', filterable: true },
    },
  },
});

// Ingest with required metadata fields
await client.collection.add('product-docs', {
  documents: [
    {
      id: 'pd-drag-drop-001',
      text: 'Drag-and-drop upload lets you add files directly to a bucket...',
      metadata: {
        version: '2.3',
        category: 'feature',
        updated_at: '2026-02-10',
        language: 'en',
      },
    },
  ],
});

// Query scoped to the right domain
const productResults = await client.search({
  collection: 'product-docs',
  query: 'how to upload files',
  topK: 5,
  filter: { category: 'guide', language: 'en' },
  mode: 'hybrid',
});

const supportResults = await client.search({
  collection: 'support-tickets',
  query: 'upload fails with 413 error',
  topK: 8,
  filter: { status: 'open', product_area: 'ingestion' },
  mode: 'hybrid',
});
```

**Collection design guidelines:**

| Principle | Rationale |
|-----------|-----------|
| One collection per domain/product area | Keeps semantic similarity scores meaningful within a shared context |
| Define schema before ingesting | Filterable fields must be declared at creation; adding them later requires re-indexing |
| Use consistent metadata keys | Inconsistent keys (`doc_type` vs `docType`) break filter queries silently |
| Aim for 10k–1M documents per collection | Smaller: consider merging. Larger: consider sharding by time or sub-domain |
| Name collections for query intent | `product-docs` not `confluence-export-2025` |

If a single query would logically need to search across multiple domains (e.g., a universal search bar), run parallel searches against each relevant collection and merge results by score on the client side.

## Reference

- https://docs.schift.io/collections/schema
- https://docs.schift.io/collections/design
