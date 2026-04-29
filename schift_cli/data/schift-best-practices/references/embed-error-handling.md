---
title: Handle AuthError, QuotaError, and rate limits properly
impact: HIGH
impactDescription: Unhandled quota or rate-limit errors crash production jobs and waste partially processed batches. Proper error handling with exponential backoff recovers automatically and avoids re-processing already-embedded documents.
tags: [embedding, error-handling, rate-limits, quota, retry]
---

## Handle AuthError, QuotaError, and rate limits properly

Schift raises three primary error types you must handle:

| Error | HTTP status | Cause |
|---|---|---|
| `AuthError` | 401 | Invalid or missing API key |
| `QuotaError` | 402 | Monthly credit limit reached |
| `RateLimitError` | 429 | Too many requests per second |

`AuthError` is a hard failure — check your key. `QuotaError` means you have exceeded your plan limits. Upgrade your plan or wait for the next billing cycle. `RateLimitError` is transient and should be retried with exponential backoff.

**Incorrect** — no error handling; a single quota error crashes the entire job:

```python
# Python - DON'T do this
from schift import Schift

client = Schift(api_key="sch_...")
texts = load_large_dataset()   # 10,000 documents

# If quota runs out halfway through, the whole job crashes
# and there is no way to resume from where it stopped
results = client.embed_batch(texts)
```

```typescript
// TypeScript - DON'T do this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });
const texts = await loadLargeDataset();

// Unhandled promise rejection on quota exceeded
const results = await client.embedBatch(texts);
```

**Correct** — catch specific errors and apply exponential backoff for rate limits:

```python
# Python - DO this
import time
from schift import Schift, AuthError, QuotaError, SchiftError

client = Schift(api_key="sch_...")

def embed_with_retry(texts: list[str], max_retries: int = 5) -> list:
    """Embed texts with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return client.embed_batch(texts)

        except AuthError:
            # Hard failure — wrong API key, do not retry
            raise RuntimeError(
                "Invalid Schift API key. Check your SCHIFT_API_KEY env var."
            )

        except QuotaError as e:
            # Credits exhausted — log and stop; retrying won't help
            raise RuntimeError(
                f"Schift quota exceeded. Check your plan limits at https://app.schift.io/billing. "
                f"Details: {e}"
            )

        except SchiftError as e:
            if e.status_code == 429:
                # Rate limit — wait and retry with exponential backoff
                wait = 2 ** attempt          # 1s, 2s, 4s, 8s, 16s
                print(f"Rate limited. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise   # Unexpected error — surface it

    raise RuntimeError(f"embed_with_retry failed after {max_retries} attempts")


# Check remaining credits before starting a large batch job
def safe_batch_embed(texts: list[str]) -> list:
    account = client.account.get()
    if account.credits_remaining < len(texts):
        raise RuntimeError(
            f"Insufficient credits: need {len(texts)}, have {account.credits_remaining}"
        )
    return embed_with_retry(texts)
```

```typescript
// TypeScript - DO this
import { Schift, AuthError, QuotaError, SchiftError } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

async function embedWithRetry(
  texts: string[],
  maxRetries = 5,
): Promise<{ embedding: number[] }[]> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await client.embedBatch(texts);

    } catch (err) {
      if (err instanceof AuthError) {
        // Hard failure — wrong API key, do not retry
        throw new Error(
          'Invalid Schift API key. Check your SCHIFT_API_KEY env var.',
        );
      }

      if (err instanceof QuotaError) {
        // Credits exhausted — log and stop
        throw new Error(
          `Schift quota exceeded. Check your plan limits at https://app.schift.io/billing. ${err.message}`,
        );
      }

      if (err instanceof SchiftError && err.statusCode === 429) {
        // Rate limit — exponential backoff
        const wait = 2 ** attempt * 1000;   // 1s, 2s, 4s, 8s, 16s
        console.warn(`Rate limited. Retrying in ${wait / 1000}s (attempt ${attempt + 1}/${maxRetries})`);
        await new Promise((resolve) => setTimeout(resolve, wait));
        continue;
      }

      throw err;   // Unexpected error — surface it
    }
  }
  throw new Error(`embedWithRetry failed after ${maxRetries} attempts`);
}

// Check credits before a large batch job
async function safeBatchEmbed(texts: string[]) {
  const account = await client.account.get();
  if (account.creditsRemaining < texts.length) {
    throw new Error(
      `Insufficient credits: need ${texts.length}, have ${account.creditsRemaining}`,
    );
  }
  return embedWithRetry(texts);
}
```

For long-running indexing jobs, track which documents have already been embedded (e.g. store their IDs in a database) so you can resume from where you left off after a `QuotaError` rather than restarting from scratch.

## Reference

- https://docs.schift.io/api/errors
- https://docs.schift.io/guides/rate-limits
