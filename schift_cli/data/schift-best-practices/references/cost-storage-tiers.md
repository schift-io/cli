---
title: Understand Storage Tier Lifecycle to Optimize Costs
impact: MEDIUM
impactDescription: Using the wrong storage tier causes either data loss (Free tier deletes S3 data after 30 days) or unnecessary cost (storing cold-access data in FAISS hot storage). Matching tier to access pattern is essential for production reliability.
tags:
  - cost
  - storage
  - tiers
  - lifecycle
  - faiss
  - s3
---

## Understand Storage Tier Lifecycle to Optimize Costs

Schift stores your vector data in two layers: FAISS (hot, in-memory vector index for fast search) and S3 (durable object storage for the original chunks and metadata). Each pricing tier has different retention policies for both layers. Mismatching your use case to the wrong tier causes data loss or unnecessary cost.

The critical mistake is treating the Free tier as suitable for production data — S3 data is deleted after 30 days, and once deleted, your collection cannot be rebuilt without re-uploading and re-embedding all source documents.

### Storage Tier Reference

| Tier | FAISS Hot Retention | S3 Retention | Use Case |
|------|--------------------|--------------|-|
| Free | 7 days | Deleted after 30 days | Development, demos, prototypes |
| Pro | 30 days | → IA after 30d → Glacier after 90d | Production applications |
| Enterprise | 90 days | → IA after 90d | High-frequency search workloads |

**Key terms:**
- **FAISS hot**: Vector index loaded in memory — sub-millisecond search latency
- **FAISS cold**: Index evicted from memory, reloaded on next query (adds ~1–3s warmup)
- **S3 Standard**: Instant retrieval, billed at standard rate
- **S3 IA** (Infrequent Access): Lower storage cost, slightly higher retrieval cost
- **S3 Glacier**: Cheapest storage, minutes-to-hours retrieval time (not suitable for live search)

### Incorrect

Using Free tier for production data — collection becomes unreachable after 30 days:

```python
# Python — Free tier for production: S3 data deleted at day 30
from schift import Schift

# Free tier API key used in production application
client = Schift(api_key="sch_free_...")

# Upload 50,000 documents — 3 months of engineering work
result = client.bucket.upload_bulk(bucket_id, documents)
print(f"Indexed {result.chunk_count} chunks")

# Day 7:  FAISS evicted — first query adds 2s cold-start latency (no warning)
# Day 30: S3 data deleted — collection.search() returns empty results with no error
# Day 31: client.query(query, collection=collection_id) → [] (silently empty, data gone)

# There is no recovery path. Source documents must be re-uploaded.
```

```typescript
// TypeScript — Free tier with no monitoring: invisible data expiry
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_free_...' });  // Free tier

// Build a production chatbot — works fine for 29 days
const answer = await client.workflow.run(workflowId, { query: userQuestion });

// Day 30+: search returns no results, LLM generates hallucinated answers
// because context is empty. No exception thrown — just silent data loss.
```

### Correct

Use Pro for production data; pin frequently-accessed collections to hot storage:

```python
# Python — Pro tier with explicit tier awareness
from schift import Schift

client = Schift(api_key="sch_pro_...")  # Pro tier

# Create collection with tier-appropriate settings
collection = client.collection.create(
    name="docs-prod",
    tier="pro",           # 30d FAISS hot, S3 → IA → Glacier lifecycle
    region="ap-northeast-2",
)

# Pin high-traffic collections to hot storage indefinitely
# (overrides the 30-day FAISS eviction, billed at hot storage rate)
client.collection.pin(collection.id, hot=True)

# Upload production data — durable beyond 90 days
result = client.bucket.upload_bulk(
    bucket_id,
    documents,
    metadata={"env": "production", "indexed_at": "2026-03-17"}
)

# Monitor cold-start risk: check FAISS warmth before high-stakes queries
status = client.collection.status(collection.id)
if not status.faiss_hot:
    client.collection.warm(collection.id)   # pre-warm before query
    # warm() is async — poll status or add a short wait for latency-sensitive paths
```

```typescript
// TypeScript — Pro tier with lifecycle-aware patterns
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_pro_...' });  // Pro tier

// Setup: create production collection with hot pin for frequently searched data
async function setupProductionCollection() {
  const collection = await client.collection.create({
    name: 'docs-prod',
    tier: 'pro',
    region: 'ap-northeast-2',
  });

  // Pin to hot storage if this collection is queried frequently (>100 queries/day)
  await client.collection.pin(collection.id, { hot: true });

  return collection.id;
}

// Runtime: check warmth before user-facing queries to avoid cold-start surprises
async function searchWithWarmGuard(collectionId: string, query: string) {
  const status = await client.collection.status(collectionId);

  if (!status.faissHot) {
    // Trigger warm-up for low-latency access on next query
    // For latency-sensitive paths, await the warm before proceeding
    await client.collection.warm(collectionId);
  }

  return client.search({
    collection: collectionId,
    query,
    topK: 5,
  });
}
```

**Tier selection guide:**

```python
# Python — choose tier based on access pattern
def choose_tier(access_frequency: str, data_criticality: str) -> str:
    """
    access_frequency: "daily" | "weekly" | "monthly" | "one-time"
    data_criticality: "production" | "staging" | "dev"
    """
    if data_criticality == "dev":
        return "free"    # OK to lose after 30 days

    if access_frequency == "daily":
        return "pro"     # FAISS stays hot 30d, pin for longer

    if access_frequency in ("weekly", "monthly") and data_criticality == "production":
        return "pro"     # S3 lifecycle keeps data, FAISS cold-starts acceptable

    if access_frequency == "one-time":
        return "free"    # Temporary indexing, no need for retention

    return "pro"         # Default to Pro for any production use
```

**Cost impact of correct tier usage (10GB collection):**

| Tier | Storage Cost/Month | Risk |
|------|--------------------|------|
| Free | $0 | Data deleted at day 30 |
| Pro | $1.50 (10GB × $0.15) | Safe for production |
| Enterprise | Custom | High-frequency, SLA-backed |

**Production checklist:**

- Never use a Free tier key in any environment where data loss is unacceptable
- Pin collections to hot storage if queried more than 50 times per day
- Monitor `collection.status().faissHot` before latency-sensitive query paths
- Set up alerts for S3 lifecycle transitions if you use collections infrequently
- Store collection IDs and creation dates — helps audit what tier data lives on

## Reference

- https://docs.schift.io/storage/tiers
- https://docs.schift.io/storage/lifecycle
- https://docs.schift.io/pricing
