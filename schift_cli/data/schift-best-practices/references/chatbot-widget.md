---
title: Build a Chatbot with Schift Search and Conversation Memory
impact: LOW
impactDescription: Production-ready chatbot with proper conversation context
tags:
  - chatbot
  - rag
  - conversation
  - memory
  - search
  - llm
---

## Build a Chatbot with Schift Search and Conversation Memory

A chatbot backed by Schift needs two things working together: vector search that retrieves relevant context from your data, and conversation history that lets the LLM give coherent follow-up answers. The most common mistake is only sending the latest user message — the LLM has no context for follow-ups like "tell me more" or "what about the second point?".

Use a retrieve-then-generate pattern:
1. User sends a message
2. Backend searches a Schift collection using the user's query
3. Retrieved chunks + conversation history are assembled into an LLM prompt
4. LLM generates a response via Schift's OpenAI-compatible proxy at `/v1/llm/chat/completions`
5. The conversation turn is stored in session

### Incorrect

Sending only the latest message to search and ignoring conversation history:

```typescript
// TypeScript — loses context on every turn
app.post('/api/chat', async (c) => {
  const { message } = await c.req.json();

  // Only uses the current message — no history
  const results = await client.search({
    collection: 'docs',
    query: message,
    topK: 4,
    mode: 'hybrid',
    rerank: true,
    rerankTopK: 4,
  });
  const context = results.map(r => r.metadata?.text ?? '').join('\n');

  // LLM has no idea what was said before
  const response = await fetch('https://api.schift.io/v1/llm/chat/completions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.SCHIFT_API_KEY}` },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: `Answer using this context:\n${context}` },
        { role: 'user', content: message },  // only the latest message
      ],
    }),
  });
  // ...
});
```

```python
# Python — same problem: no history, no context carryover
@app.post("/api/chat")
async def chat(body: ChatRequest):
    results = client.query(body.message, collection="docs", top_k=4)  # no history used
    context = "\n".join((r.get("metadata") or {}).get("text", "") for r in results)
    # Stateless: every call is a fresh conversation
```

Without history, the LLM cannot answer follow-ups, cannot refer back to earlier responses, and produces answers that feel disconnected and robotic.

### Correct

Maintain session-based conversation history, use the last 3–5 messages for search context, and pass full history to the LLM:

```typescript
// server.ts — Hono backend with session memory and Schift RAG
import { Hono } from 'hono';
import { Schift } from '@schift-io/sdk';

const app = new Hono();
const client = new Schift({ apiKey: process.env.SCHIFT_API_KEY! });

// In-memory session store (swap for Redis in production)
const sessions = new Map<string, Array<{ role: string; content: string }>>();

const COLLECTION_ID = 'col_your_collection';
const SCHIFT_LLM_URL = 'https://api.schift.io/v1/llm/chat/completions';

app.post('/api/chat', async (c) => {
  const { message, sessionId } = await c.req.json<{
    message: string;
    sessionId: string;
  }>();

  // 1. Load or initialize conversation history for this session
  const history = sessions.get(sessionId) ?? [];

  // 2. Build search query from current message + last 2 turns for context
  //    This helps disambiguate follow-ups like "tell me more about that"
  const recentContext = history
    .slice(-4)  // last 2 user+assistant pairs
    .map(m => m.content)
    .join(' ');
  const searchQuery = `${recentContext} ${message}`.trim();

  // 3. Retrieve relevant chunks from Schift
  const results = await client.search({
    collection: COLLECTION_ID,
    query: searchQuery,
    topK: 4,
    mode: 'hybrid',
    rerank: true,
    rerankTopK: 4,
  });
  const retrievedContext = results.map(r => r.metadata?.text ?? '').join('\n\n');

  // 4. Assemble messages: system prompt + history + new user message
  //    Keep last 10 turns to stay within token limits
  const trimmedHistory = history.slice(-10);
  const messages = [
    {
      role: 'system',
      content: [
        'You are a helpful assistant. Answer based on the provided context.',
        'If the context does not contain the answer, say so honestly.',
        '',
        '## Context',
        retrievedContext || '(no relevant context found)',
      ].join('\n'),
    },
    ...trimmedHistory,
    { role: 'user', content: message },
  ];

  // 5. Call LLM via Schift's OpenAI-compatible proxy
  //    /v1/llm/chat/completions supports the same format as OpenAI
  const llmResponse = await fetch(SCHIFT_LLM_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${process.env.SCHIFT_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages,
      temperature: 0.3,  // lower temp for factual Q&A
    }),
  });

  const llmData = await llmResponse.json<{
    choices: Array<{ message: { content: string } }>;
  }>();
  const assistantMessage = llmData.choices[0].message.content;

  // 6. Store this turn in session history
  history.push({ role: 'user', content: message });
  history.push({ role: 'assistant', content: assistantMessage });
  sessions.set(sessionId, history);

  return c.json({
    response: assistantMessage,
    sources: results.map(r => ({ id: r.id, score: r.score })),
  });
});

// Clear session on explicit reset
app.delete('/api/chat/:sessionId', (c) => {
  sessions.delete(c.req.param('sessionId'));
  return c.json({ cleared: true });
});

export default app;
```

**Python (FastAPI) alternative:**

```python
# main.py — FastAPI equivalent
from fastapi import FastAPI
from pydantic import BaseModel
from schift import Schift
import httpx, os

app = FastAPI()
client = Schift(api_key=os.environ["SCHIFT_API_KEY"])

# In-memory store; swap for Redis in production
sessions: dict[str, list[dict]] = {}

COLLECTION_ID = "col_your_collection"
SCHIFT_LLM_URL = "https://api.schift.io/v1/llm/chat/completions"

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/api/chat")
async def chat(body: ChatRequest):
    history = sessions.setdefault(body.session_id, [])

    # Build search query from recent conversation context
    recent = " ".join(m["content"] for m in history[-4:])
    search_query = f"{recent} {body.message}".strip()

    # Retrieve from Schift
    results = client.query(
        search_query,
        collection=COLLECTION_ID,
        top_k=4,
        rerank=True,
        rerank_top_k=4,
    )
    context = "\n\n".join((r.get("metadata") or {}).get("text", "") for r in results)

    # Assemble messages
    messages = [
        {
            "role": "system",
            "content": f"Answer based on context. Be honest if unsure.\n\n## Context\n{context or '(none)'}",
        },
        *history[-10:],
        {"role": "user", "content": body.message},
    ]

    # Call Schift's LLM proxy (OpenAI-compatible)
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            SCHIFT_LLM_URL,
            headers={"Authorization": f"Bearer {os.environ['SCHIFT_API_KEY']}"},
            json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.3},
        )
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]

    # Save turn
    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": answer})

    return {"response": answer, "sources": [{"id": r.id, "score": r.score} for r in results]}
```

**Production considerations:**

- Replace the in-memory `sessions` map with Redis (`ioredis` / `redis-py`) keyed by session ID with a TTL (e.g. 30 minutes)
- Cap `trimmedHistory` at 10 turns to keep the prompt within model context limits
- Use a lower `temperature` (0.1–0.4) for factual chatbots; higher (0.6–0.8) for creative assistants
- Schift's `/v1/llm/chat/completions` proxy accepts the same request format as OpenAI — you can swap models by changing the `model` field without changing any other code

## Reference

- https://docs.schift.io/llm/chat-completions
- https://docs.schift.io/search/overview
