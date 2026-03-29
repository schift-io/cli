# Schift CLI

Command-line interface for Schift, the operational layer for bucket ingest, vector search, benchmark runs, and model migration rollouts.

## What it covers

- Authenticate against the Schift API
- Upload files into a bucket and track ingest jobs
- Inspect the embedding model catalog
- Generate single or batch embeddings
- Create and inspect vector collections
- Run bucket or collection search from the terminal
- Benchmark a source-to-target migration before rollout
- Fit and execute projection-based migrations
- Inspect usage summaries

## Installation

From this repository:

```bash
cd sdk/cli
python3 -m pip install -e .
```

For local development with test dependencies:

```bash
cd sdk/cli
python3 -m pip install -e '.[dev]'
```

The package installs a `schift` executable via the console entry point in `pyproject.toml`.

## Configuration

The CLI reads configuration from two places:

1. `SCHIFT_API_KEY`
2. `~/.schift/config.json`

If both are present, `SCHIFT_API_KEY` wins.

The API base URL is resolved as:

1. `SCHIFT_API_URL`
2. `https://api.schift.io/v1`

`schift auth login` stores the API key in `~/.schift/config.json` and writes the file with `0600` permissions.

Example:

```bash
export SCHIFT_API_KEY=sch_your_key_here
export SCHIFT_API_URL=http://localhost:8080/v1
```

## Quick Start

```bash
schift auth login
schift auth status

schift upload ./handbook.pdf --bucket company-docs
schift jobs list --bucket company-docs
schift search "revenue report" --bucket company-docs --top-k 5

schift catalog list
schift catalog get openai/text-embedding-3-large

schift embed "hello world" --model openai/text-embedding-3-large

schift db create my-docs --dim 3072 --metric cosine
schift db list
schift search "revenue report" --collection my-docs --top-k 5

schift bench \
  --source openai/text-embedding-3-large \
  --target google/gemini-embedding-004 \
  --data ./queries.jsonl

schift migrate fit \
  --source openai/text-embedding-3-large \
  --target google/gemini-embedding-004 \
  --sample 0.1

schift migrate run \
  --projection proj_abc123 \
  --db pgvector://user:password@localhost:5432/app \
  --dry-run
```

## Command Groups

| Command | Purpose |
| --- | --- |
| `schift auth ...` | Manage local authentication state |
| `schift catalog ...` | Browse supported embedding models |
| `schift embed ...` | Generate embeddings from text |
| `schift bench ...` | Evaluate migration quality between two models |
| `schift migrate ...` | Fit a projection and apply it to a database |
| `schift db ...` | Create, list, and inspect collections |
| `schift upload ...` | Upload files into a bucket |
| `schift jobs ...` | Inspect, reprocess, and cancel ingest jobs |
| `schift search ...` | Run bucket or collection search |
| `schift query ...` | Compatibility alias for collection search |
| `schift usage ...` | Show aggregated usage and billing summary |

## Authentication

```bash
schift auth login
schift auth status
schift auth logout
```

- `login` prompts for an API key and stores it in the config file.
- `status` reports whether the CLI is using the environment variable or the config file.
- `logout` removes the stored key from the config file. It does not unset `SCHIFT_API_KEY` from your shell.

## Catalog Commands

List all models:

```bash
schift catalog list
```

Show one model:

```bash
schift catalog get openai/text-embedding-3-large
```

Output is rendered as a Rich table or key-value panel and typically includes provider, dimensions, token limit, status, and description.

## Embedding Commands

Single text:

```bash
schift embed "quarterly revenue report" --model openai/text-embedding-3-large
```

The CLI prints a success line plus a short preview of the first embedding values instead of dumping the full vector.

Batch mode:

```bash
schift embed batch \
  --file ./texts.jsonl \
  --model google/gemini-embedding-004 \
  --output ./embeddings.jsonl
```

Input format for `--file`:

```json
{"text":"First document"}
{"text":"Second document"}
```

Output format for `--output`:

```json
{"text":"First document","embedding":[0.123,0.456]}
{"text":"Second document","embedding":[0.789,0.012]}
```

If `--output` is omitted, the CLI prints only a summary count and embedding dimension.

## Collection Commands

Create a collection:

```bash
schift db create my-docs --dim 3072 --metric cosine
```

List collections:

```bash
schift db list
```

Inspect one collection:

```bash
schift db stats my-docs
```

`db list` prints a table with collection name, dimensions, metric, vector count, and creation time. `db stats` prints a detailed panel with index and storage metadata when the API returns it.

## Upload Command

```bash
schift upload ./handbook.pdf ./policy.md --bucket company-docs
```

- The CLI creates the bucket when it does not exist yet.
- `--ocr-strategy`, `--chunk-size`, and `--chunk-overlap` pass ingest overrides through to the API.
- Output includes the created ingest job IDs so you can track readiness immediately.

## Jobs Commands

```bash
schift jobs list --bucket company-docs
schift jobs get job_123
schift jobs reprocess job_123
```

- `jobs list` filters by bucket, status, and limit.
- `jobs get` is the inspect surface for one job.
- `jobs reprocess` and `jobs cancel` are the operational recovery paths when ingest needs attention.

## Search Command

```bash
schift search \
  "revenue guidance" \
  --collection my-docs \
  --top-k 10 \
  --model openai/text-embedding-3-large \
  --threshold 0.8
```

- Pass exactly one of `--collection` or `--bucket`.
- `--model` is optional.
- `--threshold` lets you filter low-score results after the API returns matches.
- `--filter` accepts the canonical JSON filter envelope for metadata and system fields.

The CLI prints a ranked result table with ID, score, and a truncated text preview.

## Query Compatibility Command

```bash
schift query "revenue guidance" --collection my-docs --top-k 10
```

`query` remains as the compatibility alias for older collection-search scripts.

## Benchmark Command

```bash
schift bench \
  --source openai/text-embedding-3-large \
  --target google/gemini-embedding-004 \
  --data ./queries.jsonl \
  --top-k 10
```

- `--data` must be an existing local file path.
- The command shows an indeterminate spinner while the API runs the benchmark.
- Output includes recall, MRR, cosine similarity, and latency metrics when available.

This command is the safety gate before a live migration. Use it first and treat low recall as a rollout blocker.

## Migration Commands

Fit a projection:

```bash
schift migrate fit \
  --source openai/text-embedding-3-large \
  --target google/gemini-embedding-004 \
  --sample 0.1
```

- `--sample` must be greater than `0` and less than or equal to `1`.
- The CLI returns a projection ID you pass into `migrate run`.

Dry-run a migration:

```bash
schift migrate run \
  --projection proj_abc123 \
  --db pgvector://user:password@localhost:5432/app \
  --dry-run \
  --batch-size 1000
```

Execute a live migration:

```bash
schift migrate run \
  --projection proj_abc123 \
  --db pgvector://user:password@localhost:5432/app \
  --batch-size 1000
```

Operational guidance:

- Start with `--dry-run`. It previews the migration without applying changes.
- A live run asks for interactive confirmation before proceeding.
- The displayed connection string masks the password in terminal output.
- Output includes processed vector count, skipped vector count, duration, and status.

## Usage Command

```bash
schift usage --period 30d
```

Accepted values are free-form strings such as `7d`, `30d`, or `90d`; the server decides what periods it supports.

The command prints:

- A summary panel with total requests, embeddings, projections, queries, storage, and cost
- A per-model usage table when the API returns `by_model`

## Error Handling and Exit Behavior

- Authentication failures raise a direct action message telling you to run `schift auth login`.
- Connection failures mention the resolved API URL and suggest checking `SCHIFT_API_URL`.
- API errors exit non-zero and surface server-provided detail text when available.
- Empty result sets are handled as normal output, not crashes.

## Local Development

Install editable dependencies:

```bash
cd sdk/cli
python3 -m pip install -e '.[dev]'
```

Useful commands:

```bash
schift --version
schift --help
schift auth --help
schift migrate --help
pytest
```

When testing against a local API:

```bash
export SCHIFT_API_URL=http://localhost:8080/v1
schift auth status
```
