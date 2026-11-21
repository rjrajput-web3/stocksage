# Dashboard deployment

**Status: built, not yet deployed** (checked 2026-11-22 IST).

The app is a fully static Next.js export (`output: "export"` in
`next.config.mjs`). Everything it renders is baked in at build time by
`scripts/prepare_data.py` into `src/data/dashboard.json`, so the deployed
page has no runtime dependency on this machine or on the live Tokenized
Stocks API.

## Why it is not live yet

The `vercel` binary on the build machine is Vercel's remote-MCP OAuth
wrapper, not the deployment CLI, and it reports `auth_status:
not_connected`. No login flow was attempted. Deploying needs one
authenticated run of the real Vercel CLI (or importing the repo in the
Vercel web UI with root directory set to `dashboard/`).

## Deploy command (from an authenticated machine)

```bash
cd dashboard
npm install
npm run build        # refreshes baked data, then builds the static export
npx vercel --prod    # or: npx vercel deploy --prebuilt --prod after `vercel build`
```

The static output lands in `dashboard/out/` and can equally be hosted on
any static host (Cloudflare Pages, GitHub Pages, Netlify) with no changes.

## After deploying

Record the live URL here and in the repo README, then rebuild + redeploy
whenever the agent completes a new decision pass or a new brief lands, so
the public page tracks the agent's record.
