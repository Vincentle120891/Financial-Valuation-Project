# Contract-Driven Development Setup Guide

## Overview

This project now uses **automated contract-driven development** to guarantee zero mismatches between React frontend and FastAPI backend. The backend Pydantic schemas are the **single source of truth**, and all TypeScript types are auto-generated from them.

## Architecture

```
Backend (Pydantic) → OpenAPI JSON → TypeScript Types → Type-Safe API Client
app/api/schemas/   → openapi.json  → schema.d.ts    → client.ts
```

## Workflow

### 1. Backend Schema Changes

When you modify any Pydantic model in `/backend/app/api/schemas/unified_step_schemas.py`:

```bash
# Step 1: Export updated OpenAPI spec
python backend/scripts/generate_spec.py

# Output: 
# ✅ Successfully exported fresh OpenAPI schema to /workspace/frontend/src/api/openapi.json
# 📊 Total endpoints: 62
# 📦 Total schemas: 67
```

### 2. Frontend Type Generation

After exporting the spec, generate TypeScript types:

```bash
cd frontend

# Install dependencies (first time only)
npm install -D openapi-typescript
npm install openapi-fetch

# Generate types from OpenAPI spec
npm run api:sync

# Output: src/api/schema.d.ts with all types
```

### 3. Usage in Components

Import the type-safe client and use it with full IntelliSense support:

```typescript
import { valuationApi } from '@/api/client';
import type { UnifiedStep4Response } from '@/types/backend-contracts';

// Type-safe API call - compiler will catch errors!
const { data, error } = await valuationApi.discoverPeers(
  'session-123',
  'AAPL',
  'international',
  'DCF',
  10
);

// data is automatically typed as UnifiedStep4Response
if (data) {
  console.log(data.peers[0].ticker); // ✅ Type-safe
  console.log(data.peers[0].similarity_score); // ✅ Type-safe
}
```

## File Structure

```
frontend/src/api/
├── openapi.json          # Auto-generated from backend (DO NOT EDIT)
├── schema.d.ts           # Auto-generated TypeScript types (DO NOT EDIT)
└── client.ts             # Type-safe API client (can extend)

frontend/src/types/
└── backend-contracts.d.ts # Convenient type re-exports (can extend)

backend/scripts/
└── generate_spec.py      # OpenAPI export script

backend/app/api/schemas/
└── unified_step_schemas.py # Single source of truth (EDIT HERE)
```

## Automated Scripts

### Backend: `generate_spec.py`

Exports FastAPI OpenAPI specification to frontend:

```bash
python backend/scripts/generate_spec.py
```

### Frontend: `api:sync`

Generates TypeScript types from OpenAPI spec:

```bash
cd frontend && npm run api:sync
```

## Benefits

### Compile-Time Safety

- ❌ Wrong endpoint path → **TypeScript error**
- ❌ Wrong field name (`maxPeers` vs `max_peers`) → **TypeScript error**
- ❌ Missing required field → **TypeScript error**
- ❌ Wrong enum value → **TypeScript error**

### No More Manual Sync

Before: 
- Backend changes → manually update markdown → manually update TypeScript interfaces → hope for the best

After:
- Backend changes → run `generate_spec.py` → run `api:sync` → done ✅

### Self-Documenting

The OpenAPI spec at `http://localhost:8000/docs` is always in sync with:
- Actual backend validation
- Frontend TypeScript types
- API client implementation

## CI/CD Integration

Add these steps to your build pipeline:

```yaml
# Example GitHub Actions step
- name: Sync API Contracts
  run: |
    python backend/scripts/generate_spec.py
    cd frontend && npm run api:sync
    
- name: Verify No Drift
  run: |
    git diff --exit-code frontend/src/api/openapi.json || \
    (echo "❌ API spec drift detected! Run generate_spec.py" && exit 1)
    
    git diff --exit-code frontend/src/api/schema.d.ts || \
    (echo "❌ TypeScript types drift detected! Run api:sync" && exit 1)
```

## Pre-Commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Check if backend schemas changed
if git diff --cached --name-only | grep -q "backend/app/api/schemas/"; then
  echo "🔍 Backend schemas changed, regenerating API spec..."
  python backend/scripts/generate_spec.py
  
  echo "🔍 Regenerating TypeScript types..."
  cd frontend && npm run api:sync
  
  # Stage the generated files
  git add frontend/src/api/openapi.json
  git add frontend/src/api/schema.d.ts
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Migration from Old API Service

Replace old axios-based calls:

**Before:**
```javascript
import { suggestPeers } from './services/api';

const peers = await suggestPeers(ticker, market, maxPeers, method, sessionId);
```

**After:**
```typescript
import { valuationApi } from './api/client';

const { data, error } = await valuationApi.discoverPeers(
  sessionId, ticker, market, method, maxPeers
);
```

## Troubleshooting

### "Module not found: openapi-fetch"

```bash
cd frontend && npm install openapi-fetch
```

### "schema.d.ts not found"

```bash
cd frontend && npm run api:sync
```

### "openapi.json is stale"

```bash
python backend/scripts/generate_spec.py
```

### Type mismatch after backend change

1. Verify backend schema change is committed
2. Re-run `generate_spec.py`
3. Re-run `api:sync`
4. Fix any TypeScript errors in components

## Best Practices

1. **Never edit** `openapi.json`, `schema.d.ts` manually
2. **Always run** both scripts when backend schemas change
3. **Commit** generated files alongside schema changes
4. **Use** the type-safe client in new code
5. **Gradually migrate** existing code to the new client

## Additional Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [openapi-typescript](https://openapi-ts.pages.dev/)
- [openapi-fetch](https://openapi-ts.pages.dev/openapi-fetch/)
- [Pydantic Models](https://docs.pydantic.dev/)
