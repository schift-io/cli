---
title: SDK Async Patterns
impact: MEDIUM
impactDescription: Calling the synchronous Schift client inside an async web framework blocks the event loop, serializing all requests and eliminating the concurrency benefit of async frameworks like FastAPI or Express.
tags: [sdk, async, fastapi, performance, python, typescript]
---

## Use the Async Client in Async Applications

The Schift Python SDK ships two client classes: `Schift` (synchronous, thread-blocking) and `AsyncSchift` (async/await, non-blocking). The TypeScript SDK is async-only and always returns Promises.

Using the synchronous Python client inside an `async def` handler does not raise an error but blocks the entire event loop for the duration of the network call. Under load, this effectively single-threads your server.

### Incorrect

```python
# Python - synchronous client blocks the event loop inside an async handler
import os
from fastapi import FastAPI
from schift import Schift  # synchronous client

app = FastAPI()
client = Schift()  # uses SCHIFT_API_KEY env var

@app.get("/search")
async def search(q: str, bucket_id: str):
    # client.bucket.search is a blocking I/O call
    # This stalls the event loop while waiting for the HTTP response
    results = client.bucket.search(bucket_id, q)
    return results
```

```typescript
// TypeScript - no sync client exists, but forgetting await is a common mistake
import { Schift } from '@schift-io/sdk';

const client = new Schift();

app.get('/search', (req, res) => {
  // Missing await - returns a Promise, not the actual results
  const results = client.bucket.search(req.query.bucketId, req.query.q);
  res.json(results);  // serializes the Promise object, not the data
});
```

### Correct

```python
# Python - use AsyncSchift with async def handlers
import os
from fastapi import FastAPI
from schift import AsyncSchift  # async client

app = FastAPI()
client = AsyncSchift()  # reads SCHIFT_API_KEY automatically

@app.get("/search")
async def search(q: str, bucket_id: str):
    results = await client.bucket.search(bucket_id, q)
    return results

# Parallel calls: use asyncio.gather to fan out multiple searches concurrently
import asyncio

@app.get("/multi-search")
async def multi_search(q: str, bucket_ids: list[str]):
    tasks = [client.bucket.search(bid, q) for bid in bucket_ids]
    results = await asyncio.gather(*tasks)
    return results
```

```typescript
// TypeScript - always await; use Promise.all for concurrent calls
import { Schift } from '@schift-io/sdk';
import express from 'express';

const app = express();
const client = new Schift(); // reads SCHIFT_API_KEY automatically

app.get('/search', async (req, res) => {
  const results = await client.bucket.search(
    req.query.bucketId as string,
    req.query.q as string
  );
  res.json(results);
});

// Parallel calls
app.get('/multi-search', async (req, res) => {
  const bucketIds = (req.query.bucketIds as string).split(',');
  const results = await Promise.all(
    bucketIds.map(id => client.bucket.search(id, req.query.q as string))
  );
  res.json(results);
});
```

For background jobs or scripts where blocking is acceptable, the synchronous `Schift` client is fine and has simpler usage. Reserve `AsyncSchift` for code running inside an event loop.

## Reference

- https://docs.schift.io/sdk/python#async
- https://docs.schift.io/sdk/typescript
