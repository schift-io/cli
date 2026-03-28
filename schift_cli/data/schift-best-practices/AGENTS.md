# schift-best-practices

> **Note:** `CLAUDE.md` is a symlink to this file.

## Overview

Embedding API, vector search, and RAG pipeline best practices from Schift. Use this skill when building embedding-powered applications, integrating Schift SDK, or optimizing vector search and retrieval.

## Structure

```
schift-best-practices/
  SKILL.md       # Main skill file - read this first
  AGENTS.md      # This navigation guide
  CLAUDE.md      # Symlink to AGENTS.md
  references/    # Detailed reference files
```

## Usage

1. Read `SKILL.md` for the main skill instructions
2. Browse `references/` for detailed documentation on specific topics
3. Reference files are loaded on-demand - read only what you need

## Reference Categories

| Priority | Category | Impact | Prefix |
|----------|----------|--------|--------|
| 1 | Embedding API | CRITICAL | `embed-` |
| 2 | Search & Retrieval | CRITICAL | `search-` |
| 3 | Authentication & SDK | CRITICAL | `sdk-` |
| 4 | Bucket Management | HIGH | `bucket-` |
| 5 | RAG Pipelines | HIGH | `rag-` |
| 6 | Cost Optimization | MEDIUM | `cost-` |
| 7 | Deployment | LOW-MEDIUM | `deploy-` |
| 8 | Chatbot Patterns | LOW | `chatbot-` |

Reference files are named `{prefix}-{topic}.md` (e.g., `embed-batch-processing.md`).

## Available References

**Embedding API** (`embed-`):
- `references/embed-batch-processing.md`
- `references/embed-multimodal.md`
- `references/embed-task-types.md`
- `references/embed-error-handling.md`

**Search & Retrieval** (`search-`):
- `references/search-similarity-tuning.md`
- `references/search-hybrid.md`
- `references/search-collection-design.md`

**Authentication & SDK** (`sdk-`):
- `references/sdk-auth-patterns.md`
- `references/sdk-async-patterns.md`

**Bucket Management** (`bucket-`):
- `references/bucket-upload.md`
- `references/bucket-organization.md`

**RAG Pipelines** (`rag-`):
- `references/rag-chunking.md`
- `references/rag-workflow-builder.md`

**Cost Optimization** (`cost-`):
- `references/cost-batching.md`
- `references/cost-storage-tiers.md`

**Deployment** (`deploy-`):
- `references/deploy-cloudrun.md`

**Chatbot Patterns** (`chatbot-`):
- `references/chatbot-widget.md`

---

*18 reference files across 8 categories*
