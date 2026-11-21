#!/usr/bin/env python3
"""
StockSage — hardened client for the Coinbase Tokenized Stocks API.

Data source: https://api.coinbase.com/v1/tokenized-stocks
Public, read-only, no API key. The catalog lives on Base mainnet only
(chain_id 8453); there is no testnet deployment of the B20 tokenized stocks.

Hard-won API notes (verified live 2026-11-21 / 2026-11-22 — see BUILDLOG.md):
- The list endpoint is the ROOT path with NO trailing slash. A trailing
  slash returns 404, so this client never adds one.
- Pagination is cursor-based: responses carry `tokens` plus an optional
  `next_page_token`; pass it back as `page_token` until it disappears.
- `nav_price` is a Chainlink-based reference/NAV value, NOT a live bid/ask
  and NOT an executable price. Feeds run 24/5: they hold the last close on
  weekends and freeze during corporate actions. ALWAYS check
  `nav_price_updated_at` staleness before using a price (see `nav_age` /
  `is_nav_stale` below) and surface stale prices honestly to readers.
- `multiplier` converts token units <-> underlying shares. Onchain it is
  WAD-scaled (ERC-8056 helpers: uiMultiplier(), balanceOfUI(),
  totalSupplyUI()); the API returns it as a plain number. It CHANGES on
  dividends and splits (e.g. SNDKc multiplier = 8), so never cache it
  across corporate actions — refetch with the record.
- The API has NO wallet positions / cost basis / PnL endpoints. Positions
  must be read onchain via balanceOfUI(); StockSage keeps its own trade
  records (AgentLog on Base Sepolia) for its simulated portfolio.
- Only a small subset of the catalog publishes a NAV price at any time
  (13 of 415 records on 2026-11-21). `nav_live_stocks()` returns exactly
  that working set — it is the only set the agent may reason about.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.coinbase.com/v1/tokenized-stocks"

# A NAV price older than this is treated as stale for display purposes.
# Feeds are 24/5, so a Friday close is ~64h old by Monday pre-market;
# the brief generator reports the exact age rather than hiding it.
DEFAULT_STALE_AFTER_SECONDS = 6 * 3600


def _get(path: str) -> dict:
    """GET JSON from the API. `path` must not start with a trailing-slash
    variant of the root list path — callers use "" for the list endpoint."""
    req = urllib.request.Request(
        BASE + path, headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def list_stocks(page_size: int = 500) -> list[dict]:
    """Return every tokenized-stock record, following cursor pagination.

    The list path is the bare root ("" — no trailing slash, which 404s).
    """
    out: list[dict] = []
    token: str | None = None
    while True:
        q = f"?page_size={page_size}" + (f"&page_token={token}" if token else "")
        d = _get(q)
        out.extend(d.get("tokens", []))
        token = d.get("next_page_token")
        if not token:
            return out


def chains() -> list[dict]:
    """Chains the catalog exists on. Currently exactly one: Base (8453)."""
    return _get("/chains").get("chains", [])


def total_supply(contract_address: str) -> dict:
    return _get(f"/total-supply/{contract_address}")


def metadata(ticker: str) -> dict:
    return _get(f"/metadata/{ticker}")


def parse_ts(value: str | None) -> datetime | None:
    """Parse an API timestamp (ISO-8601, usually with a trailing 'Z')."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def nav_age_seconds(stock: dict, now: datetime | None = None) -> float | None:
    """Age in seconds of the stock's NAV price, or None if unpublished."""
    ts = parse_ts(stock.get("nav_price_updated_at"))
    if ts is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - ts).total_seconds())


def is_nav_stale(
    stock: dict,
    stale_after: float = DEFAULT_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> bool:
    """True when the NAV price is older than `stale_after` seconds.

    A stock with no NAV timestamp at all counts as stale/unusable.
    """
    age = nav_age_seconds(stock, now=now)
    return age is None or age > stale_after


def nav_live_stocks(
    stocks: list[dict] | None = None,
    *,
    require_fresh: bool = False,
    stale_after: float = DEFAULT_STALE_AFTER_SECONDS,
) -> list[dict]:
    """Return only the records that currently publish a NAV price.

    This is the agent's working set: every other record in the catalog has
    no reference price to reason about. With `require_fresh=True`, records
    whose NAV is stale (weekend hold, frozen feed) are also excluded —
    leave it False for display flows that label staleness honestly, True
    for decision flows that must not act on old prices.
    """
    if stocks is None:
        stocks = list_stocks()
    live = [s for s in stocks if s.get("nav_price")]
    if require_fresh:
        live = [s for s in live if not is_nav_stale(s, stale_after=stale_after)]
    return live


def catalog_summary(stocks: list[dict] | None = None) -> dict:
    """Small factual summary used by the brief generator and build log."""
    if stocks is None:
        stocks = list_stocks()
    live = nav_live_stocks(stocks)
    return {
        "records": len(stocks),
        "nav_live": len(live),
        "nav_live_tickers": sorted(s["symbol"] for s in live),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    t0 = time.time()
    summary = catalog_summary()
    print(f"catalog: {summary['records']} records | NAV-live: {summary['nav_live']}")
    print("NAV-live tickers:", ", ".join(summary["nav_live_tickers"]))
    for s in sorted(nav_live_stocks(), key=lambda x: x["symbol"]):
        age = nav_age_seconds(s)
        age_txt = f"{age / 3600:.1f}h old" if age is not None else "no timestamp"
        print(
            f"{s['symbol']:<8} NAV ${s['nav_price']}  ({age_txt})  "
            f"mult {s.get('multiplier')}  updated {s.get('nav_price_updated_at')}"
        )
    print(f"fetch took {time.time() - t0:.1f}s")
