# dashboard/

The public StockSage dashboard — a single-page, fully static Next.js site:

- **Simulated portfolio** — virtual cash, positions and total value, read
  from `agent/state/portfolio.json`.
- **Latest decision pass** — every decision from the agent's most recent
  run, with its written reason.
- **NAV-live watchlist** — the tokenized stocks currently publishing a NAV
  reference price, fetched live from the Coinbase Tokenized Stocks API at
  build time, with honest staleness labels (a held weekend close is called
  out as exactly that).
- **Latest brief** — the newest `briefs/*.md`, rendered in full.
- **Onchain log status** — AgentLog deployment state and the count of
  decisions queued for Base Sepolia, with explorer links.

## How it works

`scripts/prepare_data.py` bakes all of the above into
`src/data/dashboard.json`; the page renders only from that file, so the
deployed site works even if the API is unreachable when someone views it.
`npm run build` re-runs the data prep before building. To rebuild the page
from the last baked data without refetching, use `npm run build:offline`.

## Develop / build

```bash
npm install
npm run build     # data prep + static export to out/
npm run dev       # local dev server
```

Deployment status and the production deploy command: see
[DEPLOYMENT.md](DEPLOYMENT.md).
