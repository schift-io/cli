---
name: schift-best-practices
description: Embedding API, vector search, and RAG pipeline best practices from Schift. Use this skill when building embedding-powered applications, integrating Schift SDK, or optimizing vector search and retrieval.
license: MIT
metadata:
  author: schift
  version: "0.1.0"
  organization: Schift
  date: March 2026
  abstract: Comprehensive embedding and vector search best practices for developers using Schift's managed embedding infrastructure. Contains rules across 8 categories covering embedding API usage, search optimization, bucket management, RAG pipelines, SDK patterns, cost optimization, deployment, and chatbot integration. Each rule includes incorrect vs. correct code examples in Python and TypeScript.
---

# Schift Best Practices

Best practices for building embedding-powered applications with Schift's managed embedding infrastructure. Covers embedding API, vector search, RAG pipelines, and deployment patterns.

## When to Apply

Reference these guidelines when:
- Calling Schift's embedding or search API
- Designing vector collections or bucket structures
- Building RAG pipelines with the workflow engine
- Integrating the Python or TypeScript SDK
- Deploying Schift-powered applications
- Optimizing cost and performance for embedding workloads
- Building chatbot or Q&A interfaces backed by Schift

## Rule Categories by Priority

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

## How to Use

Read individual rule files for detailed explanations and code examples:

```
references/embed-batch-processing.md
references/search-similarity-tuning.md
references/sdk-auth-patterns.md
```

Each rule file contains:
- Brief explanation of why it matters
- Incorrect code example with explanation
- Correct code example with explanation
- Performance impact or cost implications
- Schift-specific notes

## Key Concepts

- **Canonical Space**: All embeddings are projected into Schift's 1024-dimensional canonical vector space, enabling cross-model compatibility
- **Bucket**: File upload → automatic OCR + chunking + embedding → searchable index
- **Workflow**: DAG-based RAG pipeline builder with block nodes
- **Task Types**: retrieval, similarity, classification, clustering, QA, fact_verification, code_retrieval
- **Modalities**: text, image, audio, video, document

## SDK Quick Start

```python
# Python
pip install schift
from schift import Schift
client = Schift(api_key="sch_...")
result = client.embed("Hello world")
```

```typescript
// TypeScript
npm install @schift-io/sdk
import { Schift } from '@schift-io/sdk';
const client = new Schift({ apiKey: 'sch_...' });
const result = await client.embed('Hello world');
```

## References

- https://docs.schift.io
- https://github.com/schift-io/schift
- https://pypi.org/project/schift/
- https://www.npmjs.com/package/@schift-io/sdk
