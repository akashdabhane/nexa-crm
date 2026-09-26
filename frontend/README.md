# NexaCRM — frontend

Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui. See the [project README](../README.md) for setup.

```bash
cp .env.example .env.local   # Supabase URL + publishable key, API URL
npm install
npm run dev                  # http://localhost:3000
npm run lint && npx tsc --noEmit && npm run build
```

- `src/proxy.ts` — Next.js 16's replacement for `middleware.ts`: refreshes the Supabase session, redirects signed-out users.
- `src/lib/api-client.ts` — Axios instance that attaches the Supabase access token to every FastAPI call.
- `src/hooks/use-resource.ts` — TanStack Query hooks (list/detail/create/update/delete) generated per resource.
- `src/hooks/use-list-state.ts` — list page state (page, search, sort, filters) kept in the URL.
- `src/features/<module>/` — each CRM module's views, forms and hooks.
