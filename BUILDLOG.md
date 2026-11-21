# StockSage — Build Log

Public, day by day: what shipped, what broke, and what the APIs taught us.
Newest first.

---

## 2026-11-22 (IST) — Day 1: repo, data layer, decision-log contract, first brief

**Shipped**

- **Repo scaffold** — `api/`, `agent/`, `contracts/`, `briefs/`, `dashboard/`
  layout; this log started.
- **Hardened API client** (`api/tokenized_stocks.py`) — full-catalog fetch
  with cursor pagination, NAV staleness helpers (`nav_age_seconds`,
  `is_nav_stale`), and `nav_live_stocks()` returning only the names that
  currently publish a NAV price — the agent's working set.
  **Live test today:** 415 catalog records, **13 NAV-live** — AAPLc, AMZNc,
  ANTc, CRCLc, GOOGLc, INTCc, METAc, MSFTc, MSTRc, NVDAc, SNDKc, SPCXc,
  TSLAc. (The set drifts: INTCc and MSFTc publish NAV today that weren't in
  yesterday's headline list.)
- **AgentLog contract** (`contracts/src/AgentLog.sol`) — minimal append-only
  decision log: `recordDecision(ticker, side, navPrice, reasonHash)` stores
  timestamp + index and emits an event; `count()` and `getRecord(i)` read it
  back. No admin functions, no value handling — by design it can never be
  edited into a prettier history. Foundry tests: 2/2 passing (write + read
  back two records; out-of-range read reverts).
- **Brief generator v0** (`briefs/generate_brief.py`) — writes today's brief
  (`briefs/2026-11-22.md`) from live API data and saves a raw snapshot JSON
  so tomorrow's brief can compute real day-over-day moves. Because it's a
  Saturday, every NAV is Friday's close (17–21 hours old) — the brief leads
  with an explicit stale-price note rather than hiding that.

**Blocked**

- **AgentLog deployment to Base Sepolia is ready but not yet live.** A fresh
  throwaway deployer wallet exists and `contracts/deploy.sh` will deploy +
  verify + record the address the moment the wallet holds testnet ETH.
  Every public Base Sepolia faucet we tried programmatically either needs
  an account login, GitHub auth, or a captcha — none of which a build script
  should fake. One human faucet visit unblocks it; everything downstream
  (first onchain decision records) is queued behind that single step.

**API gotchas learned (from prep + today's live run)**

- The list endpoint is the root path with **no trailing slash** — a trailing
  slash returns 404.
- `nav_price` is a Chainlink-based **reference/NAV value, not a bid/ask**.
  Feeds run 24/5: weekend values are the held Friday close, and feeds freeze
  during corporate actions. Always check `nav_price_updated_at`.
- `multiplier` converts token units ↔ shares and **changes on dividends and
  splits** — SNDKc sits at 8 today, several others at ~1.0005 (a dividend
  drip, not exactly 1). Never cache it across corporate actions.
- Tokens are **B20 native precompiles** (8 decimals) — there is no per-token
  contract to read on a block explorer; the API + Chainlink feeds are the
  data surface.
- The API has **no wallet/PnL endpoints** — positions would be read onchain
  via `balanceOfUI()`; our simulated portfolio keeps its own records.
- Tokenized stocks exist on **Base mainnet only** — no Sepolia deployment —
  so the product reads live mainnet *data* (free) and puts the agent's own
  log on Sepolia ($0).

**Next (Nov 23):** strategy engine with published rules + paper portfolio
state; first simulated decisions; faucet unblock → AgentLog live on Sepolia.
