---
title: Bucket Organization by Data Domain
impact: MEDIUM
impactDescription: One bucket per upload session inflates bucket count, fragments the FAISS index, and makes cross-document search impossible without aggregating results manually. Long-lived domain buckets give better search quality and simpler code.
tags: [bucket, organization, architecture, faiss, search]
---

## Organize Buckets by Data Domain, Not by Upload Session

A Schift bucket maintains a single FAISS index over all documents ever uploaded to it. Search over a bucket queries that entire index in one call. When you create a new bucket for every upload session, each bucket becomes a silo — you lose the ability to search across related documents without fanning out to every bucket and merging results yourself.

Design buckets around stable data domains: what set of documents belongs together conceptually? That set is a bucket.

### Incorrect

```python
# Python - new bucket per upload session
# After 10 uploads you have 10 buckets, none searchable together
from schift import Schift
from datetime import datetime

client = Schift()

def upload_weekly_reports(files: list[str]):
    # Creates a new bucket every time this function runs
    bucket = client.bucket.create(f"reports-{datetime.now().isoformat()}")
    job = client.bucket.upload(bucket.id, files=files)
    job.wait()
    return bucket.id

# Searching now requires querying every bucket and merging manually
def search_all_reports(query: str) -> list:
    buckets = client.bucket.list()  # grows every week
    all_hits = []
    for b in buckets:
        results = client.bucket.search(b.id, query)
        all_hits.extend(results.hits)
    all_hits.sort(key=lambda h: h.score, reverse=True)
    return all_hits
```

```typescript
// TypeScript - same anti-pattern
import { Schift } from '@schift-io/sdk';

const client = new Schift();

async function uploadWeeklyReports(files: string[]) {
  const bucket = await client.bucket.create(`reports-${Date.now()}`);
  const job = await client.bucket.upload(bucket.id, { files });
  await job.wait();
  return bucket.id;
}
```

### Correct

```python
# Python - one bucket per data domain, append files over time
from schift import Schift

client = Schift()

# Provision once (e.g., at app startup or in a migration script)
def get_or_create_bucket(name: str) -> str:
    existing = [b for b in client.bucket.list() if b.name == name]
    if existing:
        return existing[0].id
    return client.bucket.create(name).id

# Reuse the same bucket across all weekly uploads
REPORTS_BUCKET = get_or_create_bucket("weekly-reports")

def upload_weekly_reports(files: list[str]):
    job = client.bucket.upload(REPORTS_BUCKET, files=files)
    job.wait()

# Single search call covers all documents ever uploaded to this bucket
def search_reports(query: str):
    return client.bucket.search(REPORTS_BUCKET, query).hits
```

```typescript
// TypeScript - same domain-first approach
import { Schift } from '@schift-io/sdk';

const client = new Schift();

async function getOrCreateBucket(name: string): Promise<string> {
  const buckets = await client.bucket.list();
  const existing = buckets.find(b => b.name === name);
  if (existing) return existing.id;
  const bucket = await client.bucket.create(name);
  return bucket.id;
}

const REPORTS_BUCKET = await getOrCreateBucket('weekly-reports');

async function uploadWeeklyReports(files: string[]) {
  const job = await client.bucket.upload(REPORTS_BUCKET, { files });
  await job.wait();
}

async function searchReports(query: string) {
  return (await client.bucket.search(REPORTS_BUCKET, query)).hits;
}
```

**Recommended domain examples:**

| Domain | Bucket name |
|--------|-------------|
| Internal knowledge base | `company-docs` |
| Product documentation | `product-manuals` |
| Legal contracts | `legal-contracts` |
| Support ticket history | `support-history` |
| Weekly reports | `weekly-reports` |

If two domains are always searched together, merge them into one bucket. If they are never searched together and have different access control requirements, keep them separate.

Each bucket has an independent FAISS index. Uploads append to the index; the index is never rebuilt from scratch unless explicitly requested.

## Reference

- https://docs.schift.io/buckets/organization
- https://docs.schift.io/buckets/faiss-index
