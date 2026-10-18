# Knowledge Across Time — Frontend

Next.js (App Router, Tailwind v4) UI for **Britannica vs. Wikipedia**: a live *Debate* between a Britannica
scholar (1768–1860) and a Wikipedia editor (2026), judged by a moderator, plus an *Ask* mode.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
# production: npm run build && npm start
```

The FastAPI backend is expected at `http://localhost:8000`.

## Mock / demo mode

- `http://localhost:3000/?mock=1` replays `public/mock-debate.json` (an "Astronomy" debate) and answers Ask with
  `public/mock-ask.json`. No backend needed.
- `?topic=Astronomy` starts a debate automatically, e.g. `/?mock=1&topic=Astronomy` for a hands-free demo recording.
- If the backend is unreachable, the UI falls back to the recorded demo automatically and shows a **Demo** banner.
- Full texts for the drawer in mock mode come from `public/mock-sources.json`; fake page scans are in `public/mock/`.

## Environment variables

| Variable                  | Default                 | Used for                                                                 |
| ------------------------- | ----------------------- | ------------------------------------------------------------------------ |
| `BACKEND_URL`             | `http://localhost:8000` | Server-side rewrite `/api/:path*` → backend (`/api/ask`, `/api/source/…`) |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Browser connects **directly** to `GET /api/debate` (SSE), needs CORS     |

The SSE stream skips the Next rewrite so responses aren't buffered.

## Layout

- `app/page.tsx` → `components/App.tsx` (header + Debate/Ask tabs)
- `components/DebateView.tsx`, `components/debate-parts.tsx`: split-screen arena, tool-call indicators,
  agreement meter, moderator rulings, verdict card
- `components/AskView.tsx`: question → answer with citation chips, sources, agent trace
- `components/citations.tsx`, `components/CitationDrawer.tsx`: `[EB:…]` / `[WP:…]` chips (red = unsupported)
  and the source drawer (fetches `/api/source/{cite_id}`, shows scan image)
- `utils/useDebate.ts`: SSE client + event reducer + mock replay; `utils/types.ts`: event contract
