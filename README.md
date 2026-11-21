# StockSage — an AI agent for tokenized stocks on Base

**Stocks Maxxing Season · Track: Agentic Stock Finance**

StockSage is an AI agent that watches Coinbase's tokenized stocks on Base
(the B20 token standard) and explains them like a smart friend — in plain
language, with real numbers and honest timestamps.

## What it does

- **Daily briefs** — a short, readable rundown of the tokenized stocks that
  publish a NAV reference price: what each one tracks, what its reference
  price is, and exactly when that price was last updated. If the feeds are
  holding a weekend close, the brief says so instead of dressing old numbers
  up as live ones.
- **A simulated portfolio, managed in the open** — the agent runs a paper
  portfolio under a published rule set (momentum + mean-reversion bands).
  Every simulated decision is written to the **AgentLog** contract on Base
  Sepolia — ticker, side, the NAV reference price at decision time, and a
  hash of the agent's written reasoning — so anyone can verify what the
  agent did and when. No real money, no real securities, ever.
- **Ask-the-agent** *(coming in v1)* — questions answered from live
  Tokenized Stocks API data plus the agent's own onchain log.

## Why onchain logging?

An agent that explains markets should be accountable for its own record.
Anchoring every simulated decision in an append-only public log means the
agent can't quietly rewrite its history — the wins and the mistakes are
equally permanent.

## Data source

Coinbase **Tokenized Stocks API** — `https://api.coinbase.com/v1/tokenized-stocks`
(public, read-only, no key). Live check on 2026-11-22: **415 token records**
on Base mainnet (chain 8453), **13 publishing a NAV reference price**
(AAPLc, AMZNc, ANTc, CRCLc, GOOGLc, INTCc, METAc, MSFTc, MSTRc, NVDAc,
SNDKc, SPCXc, TSLAc). NAV is a Chainlink-based reference value, not an
executable price — StockSage always labels it as such.

The tokenized stocks themselves exist on Base mainnet only; the agent's own
activity (its decision log) lives on Base Sepolia testnet, so the whole
product runs at $0 with no real assets involved.

## Repo layout

- `api/` — hardened Tokenized Stocks API client (pagination, NAV staleness checks)
- `agent/` — strategy engine + simulated portfolio (in build)
- `contracts/` — AgentLog (Foundry project; Base Sepolia)
- `briefs/` — the daily brief generator and the brief archive
- `dashboard/` — public dashboard (in build)

Build history, day by day, including what broke: [BUILDLOG.md](BUILDLOG.md).

## Fine print

Research and education only. **Not financial advice.** Nothing here is a
recommendation to buy or sell anything. Tokenized stocks are Regulation S
instruments; this product enables no trading for U.S. users and executes no
real trades for anyone.
