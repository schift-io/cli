---
title: Use WorkflowBuilder for Reproducible RAG Pipelines
impact: HIGH
impactDescription: Ad-hoc inline RAG code is hard to test, version, or share. WorkflowBuilder defines RAG as a versioned DAG — reproducible across environments, observable via run history, and shareable as templates.
tags:
  - rag
  - workflow
  - dag
  - workflowbuilder
  - pipeline
  - observability
---

## Use WorkflowBuilder for Reproducible RAG Pipelines

Embedding retrieval + reranking + LLM generation is a multi-step pipeline. When this logic lives as scattered inline code, it becomes impossible to test individual steps in isolation, reproduce a specific run for debugging, or share the pipeline as a reusable template across projects.

Schift's workflow engine models RAG pipelines as directed acyclic graphs (DAGs). Each step is a typed node (retrieve, rerank, generate, filter, transform). The `WorkflowBuilder` API in TypeScript (and its Python equivalent) lets you define, version, and register these pipelines as first-class resources. You run them by ID, and every run is logged — input, intermediate results, output — for debugging and evaluation.

### Incorrect

Inline search + LLM call logic scattered across the application:

```typescript
// TypeScript — ad-hoc RAG scattered across application code
import { Schift } from '@schift-io/sdk';
import OpenAI from 'openai';

const client = new Schift({ apiKey: 'sch_...' });
const openai = new OpenAI();

// This logic is duplicated in routes/chat.ts, routes/search.ts, scripts/batch.ts
// No versioning, no run history, impossible to A/B test
async function answerQuestion(question: string) {
  // Step 1: retrieve — hardcoded params, no way to tune per environment
  const results = await client.search({
    collection: collectionId,
    query: question,
    topK: 5,
  });

  // Step 2: no reranking step — order determined by vector score alone
  const context = results.map(r => r.metadata?.text ?? '').join('\n\n');

  // Step 3: generate — prompt template hardcoded here, not versioned
  const completion = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      { role: 'system', content: 'Answer based on context.' },
      { role: 'user', content: `Context:\n${context}\n\nQuestion: ${question}` },
    ],
  });

  return completion.choices[0].message.content;
  // No logging of which chunks were retrieved, no run ID, no eval surface
}
```

```python
# Python — same problem: logic copy-pasted across scripts, no observability
from schift import Schift
from openai import OpenAI

schift = Schift(api_key="sch_...")
openai = OpenAI()

def answer(question: str) -> str:
    results = schift.search(collection_id, question, top_k=5)
    context = "\n\n".join(r.text for r in results)
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Answer based on context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQ: {question}"},
        ]
    )
    return resp.choices[0].message.content
    # No run ID, no intermediate state, cannot replay or debug
```

When this breaks in production, you cannot inspect which chunks were retrieved, which reranking score caused a bad answer, or compare two versions of the pipeline.

### Correct

Define the pipeline once as a versioned workflow, run it by ID:

```typescript
// TypeScript — WorkflowBuilder: define once, run anywhere, fully observable
import { Schift, WorkflowBuilder } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_...' });

// Define the DAG — do this once during setup (e.g., in a migration script)
const graph = new WorkflowBuilder()
  .addNode({
    id: 'retrieve',
    type: 'retrieve',
    config: {
      collectionId: 'col_docs_prod',
      topK: 10,
      mode: 'hybrid',
      taskType: 'qa',
    },
  })
  .addNode({
    id: 'rerank',
    type: 'rerank',
    config: {
      model: 'schift-reranker-v1',
      topN: 3,       // keep only the top 3 after reranking
    },
  })
  .addNode({
    id: 'generate',
    type: 'generate',
    config: {
      model: 'gpt-4o',
      systemPrompt: 'Answer the question using only the provided context. If unsure, say so.',
      maxTokens: 512,
    },
  })
  .addEdge('retrieve', 'rerank')   // retrieve → rerank
  .addEdge('rerank', 'generate')   // rerank → generate
  .build();

// Register the workflow — returns a versioned workflow ID
const workflow = await client.workflow.create('docs-qa-v1', graph);
console.log(workflow.id);  // wf_abc123 — store this in your config

// Run the workflow — every run gets a run ID
const run = await client.workflow.run(workflow.id, {
  query: 'What are the latency benchmarks for the v2 model?',
});

console.log(run.runId);          // run_xyz789 — for debugging
console.log(run.output.answer);  // final generated answer
console.log(run.steps.retrieve.chunks);  // intermediate: which chunks retrieved
console.log(run.steps.rerank.chunks);    // intermediate: which chunks survived reranking
```

```python
# Python — same workflow pattern
from schift import Schift

client = Schift(api_key="sch_...")

# Build the graph as a dict (Python SDK uses graph spec format)
graph = {
    "nodes": [
        {
            "id": "retrieve",
            "type": "retrieve",
            "config": {
                "collection_id": "col_docs_prod",
                "top_k": 10,
                "score_threshold": 0.70,
                "task_type": "qa",
            },
        },
        {
            "id": "rerank",
            "type": "rerank",
            "config": {"model": "schift-reranker-v1", "top_n": 3},
        },
        {
            "id": "generate",
            "type": "generate",
            "config": {
                "model": "gpt-4o",
                "system_prompt": "Answer using only the provided context.",
                "max_tokens": 512,
            },
        },
    ],
    "edges": [
        {"from": "retrieve", "to": "rerank"},
        {"from": "rerank", "to": "generate"},
    ],
}

# Register once
workflow = client.workflow.create("docs-qa-v1", graph)

# Run — returns structured run result with full step history
run = client.workflow.run(workflow.id, {"query": "What are the latency benchmarks?"})

print(run.run_id)               # for debugging
print(run.output["answer"])     # final answer
print(run.steps["retrieve"])    # which chunks were retrieved
print(run.steps["rerank"])      # which chunks survived reranking
```

**Why WorkflowBuilder over inline code:**

| Concern | Inline Code | WorkflowBuilder |
|---------|-------------|-----------------|
| Versioning | Manual, error-prone | Built-in (v1, v2, ...) |
| Observability | None | Full run history with step-level traces |
| Testing | Full integration test required | Each node testable in isolation |
| Sharing | Copy-paste | Export/import workflow templates |
| A/B testing | Requires code branching | Run two workflow IDs, compare run metrics |
| Prompt updates | Redeploy required | Update workflow node config, no code change |

Store the workflow ID in your application config (environment variable or database). If you need to update the pipeline — change `topK`, swap the reranker, update the system prompt — create a new workflow version and update the config, with no application code changes.

## Reference

- https://docs.schift.io/workflows/builder
- https://docs.schift.io/workflows/run-history
