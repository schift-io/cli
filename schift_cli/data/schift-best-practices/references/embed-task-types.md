---
title: Specify task_type for optimal embedding quality
impact: HIGH
impactDescription: Using the default task_type for every use case can silently degrade retrieval accuracy by 10-30%. Schift optimizes embeddings differently depending on whether the vector will be used for search, classification, clustering, or other tasks.
tags: [embedding, task-type, retrieval, classification, quality]
---

## Specify task_type for optimal embedding quality

Schift supports seven task types that control how the embedding model is fine-tuned for your specific use case. The default (`retrieval`) is a safe starting point, but explicitly setting the correct task type produces better embeddings and downstream results.

| task_type | When to use |
|---|---|
| `retrieval` | Asymmetric search — query against document corpus |
| `similarity` | Symmetric similarity — comparing two pieces of text |
| `classification` | Labeling or categorizing text |
| `clustering` | Grouping documents by topic |
| `QA` | Question-answering — question against answer pairs |
| `fact_verification` | Claim against evidence matching |
| `code_retrieval` | Natural-language query against code snippets |

**Incorrect** — using default `task_type` for every case reduces embedding quality:

```python
# Python - DON'T do this
from schift import Schift

client = Schift(api_key="sch_...")

# Indexing documents for search — no task_type set
doc_embedding = client.embed("The Eiffel Tower is in Paris.")

# Classifying customer feedback — no task_type set
label_embedding = client.embed("This product is terrible!")

# Searching code — no task_type set
code_query = client.embed("function that sorts a list")
```

```typescript
// TypeScript - DON'T do this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// All three use cases use the same default — suboptimal for each
const docEmbedding  = await client.embed('The Eiffel Tower is in Paris.');
const labelEmbedding = await client.embed('This product is terrible!');
const codeQuery      = await client.embed('function that sorts a list');
```

**Correct** — match `task_type` to your use case:

```python
# Python - DO this
from schift import Schift

client = Schift(api_key="sch_...")

# Asymmetric document search: index documents as "retrieval"
doc_embedding = client.embed(
    "The Eiffel Tower is in Paris.",
    task_type="retrieval",
)

# Classifying customer feedback
label_embedding = client.embed(
    "This product is terrible!",
    task_type="classification",
)

# Natural-language query against a code repository
code_query = client.embed(
    "function that sorts a list",
    task_type="code_retrieval",
)

# QA: embed question against pre-embedded answers
question_vec = client.embed(
    "What year was the Eiffel Tower built?",
    task_type="QA",
)

# Fact verification: claim against supporting evidence
claim_vec = client.embed(
    "The Eiffel Tower was built in 1889.",
    task_type="fact_verification",
)

# Batch embed with task_type
docs = ["Doc A content...", "Doc B content...", "Doc C content..."]
results = client.embed_batch(docs, task_type="retrieval")
```

```typescript
// TypeScript - DO this
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Asymmetric document search
const docEmbedding = await client.embed(
  'The Eiffel Tower is in Paris.',
  { taskType: 'retrieval' },
);

// Classification
const labelEmbedding = await client.embed(
  'This product is terrible!',
  { taskType: 'classification' },
);

// Code search
const codeQuery = await client.embed(
  'function that sorts a list',
  { taskType: 'code_retrieval' },
);

// QA
const questionVec = await client.embed(
  'What year was the Eiffel Tower built?',
  { taskType: 'QA' },
);

// Batch with task type
const docs = ['Doc A content...', 'Doc B content...', 'Doc C content...'];
const results = await client.embedBatch(docs, { taskType: 'retrieval' });
```

Use the same `task_type` when indexing documents and when embedding queries — mixing task types in the same collection degrades search quality. For collections that serve multiple use cases, create separate collections per task type.

## Reference

- https://docs.schift.io/api/embed#task-type
- https://docs.schift.io/concepts/task-types
