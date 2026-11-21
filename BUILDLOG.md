# StockSage — Build Log

Public, day by day: what shipped, what broke, and what the APIs taught us.
Newest first.

---

## 2026-11-24 (IST) — Day 3: public dashboard v1 (pulled forward; built 2026-11-22)

**Shipped**

- **Public dashboard** (`dashboard/`) — a single-page, fully static Next.js
  site in the premium dark style the project uses everywhere: Space
  Grotesk headings, Inter body, and a custom geometric logo (a leaf whose
  vein is a rising chart line). One page, five sections:
  - the **simulated portfolio** — virtual cash, positions and total value
    straight from the agent's state file, with the "Simulated portfolio.
    Not financial advice." note up top, not buried;
  - the **latest decision pass** — all 13 decisions from pass #1, each
    with the agent's full written reason (13 HOLDs, and why);
  - the **NAV-live watchlist** — the 13 names with NAV reference prices,
    last-update timestamps and freshness badges; because every price is a
    held weekend close right now, a banner says so in plain words:
    "Price held from Friday close";
  - the **latest brief**, rendered in full;
  - the **onchain log** card — AgentLog is not deployed yet, and the page
    says that too, with the 13 queued decisions counted and a Basescan
    (Sepolia) link ready for the contract address.
- **Baked-data architecture** — `dashboard/scripts/prepare_data.py` pulls
  the portfolio state, the decision history, the live watchlist (via the
  hardened `api/` client) and the newest brief into one JSON at build
  time; the page renders only from that file. If the API is unreachable
  when someone views the page, nothing breaks — and if it is unreachable
  at *build* time, the prep falls back to the portfolio's seeded reference
  prices and labels the source honestly.

**Verified**

- `npm install` + `npm run build` pass clean; the static export was
  checked section by section (portfolio totals, all 13 decisions, all 13
  watchlist names, the brief, the disclaimers).

**Not yet live**

- The `vercel` binary on the build machine turned out to be Vercel's
  remote-MCP OAuth wrapper rather than the deployment CLI, and it is not
  connected — so no login was attempted and the site is built but not
  deployed. The exact production deploy command is recorded in
  `dashboard/DEPLOYMENT.md`.

---

## 2026-11-23 (IST) — Day 2: strategy engine + paper portfolio

**Shipped**

- **Published rule set** (`agent/RULES.md`) — the agent's rules are written
  down in plain language before the code that follows them: $100,000
  virtual capital; only NAV-live names; a freshness gate (a NAV more than
  6 hours old is never acted on); a trailing reference per name (seeded
  from yesterday's snapshot, then rolled forward each run); a **momentum
  band** (simulated buy of one $5,000 step when NAV is up ≥ 1.5% vs the
  reference); a **mean-reversion band** (same step when NAV is down
  ≥ 2.0%); caps of $10,000 per name and $60,000 total exposure; one
  decision per name per run, alphabetical, so results are reproducible.
  This first version deliberately has no exit rule — that is stated in
  the rules, not hidden.
- **Strategy engine** (`agent/engine.py`) — a pure function of (prices,
  references, portfolio): same inputs, same decisions, verified by running
  the pass twice and diffing against the recorded history.
- **Paper portfolio** (`agent/portfolio.py`, state in
  `agent/state/portfolio.json`) — virtual cash, positions in token units
  with share-equivalents via each token's multiplier, weighted average
  NAV, and a full decision history with written reasons.
- **Runner** (`python3 -m agent.run`) — fetch → decide → apply → print a
  plain-language summary → anchor onchain if possible, else queue.

**First real run (today)**

- 13 NAV-live names, **13 HOLDs, 0 simulated buys** — the honest outcome,
  twice over: every NAV is Friday's close held over the weekend (17.6–21.3
  hours old, so the freshness gate blocks action), and the held prices are
  unchanged versus yesterday's snapshot (0.00% moves, inside both bands).
  Each hold is recorded with its reason; "did nothing, and here is why"
  is part of the public record by design.
- Portfolio after pass #1: $100,000.00 virtual cash, no positions,
  references rolled forward for all 13 names.

**Onchain status**

- AgentLog is still **not deployed**: the throwaway deployer wallet's Base
  Sepolia balance is 0 (checked onchain today). The runner now automates
  the whole path — the moment the wallet is funded it deploys via
  `contracts/deploy.sh` and starts writing decisions; until then today's
  13 decisions sit in `agent/state/pending_onchain.json` with their
  reason hashes, queued for logging. (One runner bug found and fixed on
  the way: the public RPC rejects requests without a User-Agent header.)

**Next (Nov 24):** dashboard v1 — portfolio curve, decision list with
explorer links once AgentLog is live, latest brief.

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

## 2026-11-22 (IST) — AgentLog deployed on Base Sepolia
- Deployer funded by Rohit (0.005 ETH testnet). AgentLog deployed: 0x7cd321F3F28e3bBb3aF4C66c19d5AabF5a70424a (tx 0x179659477b69f5dbe8317b31240e9775bd781faed0b7dea1e339f3d9544793f8).
- First onchain anchoring done: 13 agent decisions written to AgentLog, count() verified = 13 on https://sepolia.basescan.org/address/0x7cd321F3F28e3bBb3aF4C66c19d5AabF5a70424a
