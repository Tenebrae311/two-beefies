# Knowledge Across Time — Frontend

Next.js (App Router, Tailwind v4) UI for **Britannica vs. Wikipedia**: a live *Debate* between a Britannica
scholar (1768–1860) and a Wikipedia editor (2026), judged by a moderator, plus an *Ask* mode and a *Cases* viewer
(documented successes / failures of the agent).

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
- `?tab=ask` / `?tab=cases` opens that tab directly, e.g. `/?mock=1&tab=cases`.
- The Cases tab reads `public/mock-cases.json` (synthetic list + per-slug records) in mock mode or when `/api/cases`
  fails.
- If the backend is unreachable, the UI falls back to the recorded demo automatically and shows a **Demo** banner.
- Full texts for the drawer in mock mode come from `public/mock-sources.json`; fake page scans are in `public/mock/`.

## Environment variables

| Variable                  | Default                 | Used for                                                                 |
| ------------------------- | ----------------------- | ------------------------------------------------------------------------ |
| `BACKEND_URL`             | `http://localhost:8000` | Server-side rewrite `/api/:path*` → backend (`/api/ask`, `/api/source/…`) |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Browser connects **directly** to `GET /api/debate` (SSE), needs CORS     |

The SSE stream skips the Next rewrite so responses aren't buffered.

## Layout

- `app/page.tsx` → `components/App.tsx` (split-screen hero + Debate/Ask/Cases tabs)
- `components/flair.tsx`: decorative pieces of the "duel across time" look: VS medallion, animated orrery
  (Britannica side), knowledge graph (Wikipedia side), edition timeline, tab icons. Theme tokens and effects
  (hero halves, `btn-duel`, `duel-frame`, `glass-card`, `scoreboard`) live in `app/globals.css`; animations respect
  `prefers-reduced-motion`.
- `components/DebateView.tsx`, `components/debate-parts.tsx`: split-screen arena, tool-call indicators,
  agreement meter, moderator rulings, verdict card
- `components/AskView.tsx`: question → answer with citation chips, sources, agent trace
- `components/citations.tsx`, `components/CitationDrawer.tsx`: `[EB:…]` / `[WP:…]` chips (red = unsupported)
  and the source drawer (fetches `/api/source/{cite_id}`, shows scan image)
- `components/evidence.tsx`: "Evidence (Nemotron Rerank)" strip under each turn / answer — per-claim support,
  anachronism rows (Britannica claim unsupported by its own sources but supported by Wikipedia), verdict panel
- `components/vision.tsx`: "Looked at the original scan" card for `inspect_page_image` / `compare_images`
  (Nemotron VL), with a lightbox; `components/trace.tsx`: tool-call trace shared by Ask and Cases
- `components/CasesView.tsx`: Cases tab (`/api/cases`, `/api/cases/{slug}`) — metrics table, grouped list, detail
- `utils/useDebate.ts`: SSE client + event reducer + mock replay; `utils/types.ts`: event contract
  (incl. `evidence` events, `tool_result.vision`, `verdict.evidence`, case records)
