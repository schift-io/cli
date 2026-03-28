---
title: SDK Authentication Patterns
impact: CRITICAL
impactDescription: Hardcoded API keys in source code are the most common cause of credential leaks. A leaked `sch_` key can drain your quota and expose your data before you notice.
tags: [sdk, auth, security, api-key]
---

## Never Hardcode API Keys

API keys must never appear as string literals in source code. Keys committed to version control or embedded in build artifacts are exposed to anyone with repository access, container image access, or build log access. Rotate immediately if a key is ever exposed.

Schift API keys follow the format `sch_` followed by a random string. Treat them like passwords.

### Incorrect

```python
# Python - key is visible in source and will leak via git history
from schift import Schift

client = Schift(api_key="sch_abc123xyz789...")  # NEVER do this
```

```typescript
// TypeScript - same problem; bundlers may embed this in client-side code
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: 'sch_abc123xyz789...' }); // NEVER do this
```

Both examples embed a literal key that will appear in `git log`, CI logs, Docker image layers, and any bundle output.

### Correct

```python
# Python - read from environment variable explicitly
import os
from schift import Schift

client = Schift(api_key=os.environ["SCHIFT_API_KEY"])

# Or rely on the SDK's automatic env-var lookup (recommended for simplicity)
# The SDK reads SCHIFT_API_KEY automatically when api_key is omitted
client = Schift()
```

```typescript
// TypeScript - read from process.env
import { Schift } from '@schift-io/sdk';

const client = new Schift({ apiKey: process.env.SCHIFT_API_KEY });

// Or rely on SDK auto-detection (reads SCHIFT_API_KEY if apiKey is omitted)
const client = new Schift();
```

Set the key in your environment:

```bash
# Local development (.envrc, never committed)
export SCHIFT_API_KEY=sch_dev_...

# CI/CD - set as a masked secret variable in your platform
# Docker / Kubernetes - inject via --env-file or a Secret resource
```

Additional best practices:
- Use **project-scoped keys** (not org-wide admin keys) so a leaked key has minimal blast radius
- Create **separate keys** for `dev`, `staging`, and `prod` environments
- **Rotate keys regularly** from the Schift dashboard; old keys can be revoked without downtime
- Add `SCHIFT_API_KEY` to `.gitignore`-adjacent `.envrc` or use a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault)

## Reference

- https://docs.schift.io/authentication
- https://docs.schift.io/sdk/python#authentication
- https://docs.schift.io/sdk/typescript#authentication
