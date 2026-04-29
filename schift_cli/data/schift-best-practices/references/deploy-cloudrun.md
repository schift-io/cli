---
title: Deploy Schift-Powered Apps on Cloud Run for Zero Idle Cost
impact: LOW-MEDIUM
impactDescription: Zero idle cost with proper Cloud Run configuration
tags:
  - deployment
  - cloud-run
  - docker
  - infrastructure
  - cost
  - scaling
---

## Deploy Schift-Powered Apps on Cloud Run for Zero Idle Cost

Cloud Run scales to zero when no traffic is coming in, so you pay nothing while your app is idle. This is ideal for Schift-backed services that handle sporadic traffic — chatbots, search APIs, document Q&A endpoints. The common mistake is deploying these on an always-on VM, which bills 24/7 regardless of actual usage.

### Incorrect

Running a Schift-powered chatbot on an always-on VM that pays for compute even during zero-traffic hours:

```bash
# Always-on EC2 / Compute Engine VM approach
# Costs ~$15–30/month even when nobody is using the app
# Manual scaling, manual restarts, no request-based autoscaling

ssh ec2-user@your-server
pm2 start server.js  # just stays running forever
```

```typescript
// server.ts — no health check, no graceful shutdown
// Deployed on an always-on VM: billed 24/7
import { Hono } from 'hono';
import { Schift } from '@schift-io/sdk';

const app = new Hono();
const client = new Schift({ apiKey: process.env.SCHIFT_API_KEY! });

app.post('/chat', async (c) => {
  const { query } = await c.req.json();
  const results = await client.collectionSearch('docs', {
    query,
    topK: 3,
    mode: 'hybrid',
  });
  return c.json({ results: results.results ?? results });
});

export default app;
// No /health endpoint → load balancer cannot confirm readiness
// No memory limit set → OOM-killed silently
```

This approach pays for a full VM instance even when traffic is zero, lacks health checks for Cloud Run readiness probes, and requires manual scaling during traffic spikes.

### Correct

Deploy on Cloud Run with `min-instances=0`, set memory for embedding operations, and expose a `/health` endpoint:

```dockerfile
# Dockerfile — multi-stage build for a minimal runtime image
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
# Copy only compiled output and production deps
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./

# Cloud Run injects PORT; default to 8080
ENV PORT=8080
EXPOSE 8080

CMD ["node", "dist/server.js"]
```

```typescript
// server.ts — production-ready Cloud Run handler
import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { Schift } from '@schift-io/sdk';

const app = new Hono();

// SCHIFT_API_KEY is injected from Cloud Run secret at runtime
const client = new Schift({ apiKey: process.env.SCHIFT_API_KEY! });

// Required: Cloud Run sends readiness/liveness probes to /health
app.get('/health', (c) => c.json({ status: 'ok' }));

app.post('/search', async (c) => {
  const { query, collection } = await c.req.json();
  const results = await client.collectionSearch(collection, {
    query,
    topK: 5,
    mode: 'hybrid',
    rerank: true,
  });
  return c.json({ results: results.results ?? results });
});

const port = Number(process.env.PORT) || 8080;
serve({ fetch: app.fetch, port });
```

```bash
# Build and push the container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/schift-app

# Deploy to Cloud Run
gcloud run deploy schift-app \
  --image gcr.io/YOUR_PROJECT/schift-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \         # scale to zero → $0 idle cost
  --max-instances 10 \
  --concurrency 80 \          # requests handled per instance before scaling out
  --timeout 300 \             # 5 min max for long embedding/search ops
  --memory 512Mi \            # minimum for embedding operations
  --set-secrets SCHIFT_API_KEY=schift-api-key:latest  # inject from Secret Manager
```

**Key settings explained:**

| Setting | Value | Why |
|---------|-------|-----|
| `min-instances` | `0` | Scales to zero when idle — $0 cost |
| `concurrency` | `80` | Cloud Run default; safe for I/O-bound search APIs |
| `timeout` | `300s` | Allows time for cold starts + embedding latency |
| `memory` | `512Mi` | Minimum for Schift SDK + embedding response buffers |
| `SCHIFT_API_KEY` | Secret Manager | Never hardcode API keys in the image |

**Cold start note:** With `min-instances=0`, the first request after idle incurs a cold start (~1–3 seconds). If your use case requires consistent low latency, set `min-instances=1` — this costs ~$5–10/month but eliminates cold starts.

## Reference

- https://docs.schift.io/deployment/cloud-run
- https://cloud.google.com/run/docs/configuring/min-instances
