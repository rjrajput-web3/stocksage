#!/usr/bin/env python3
"""
StockSage dashboard — data prep.

Bakes everything the static dashboard renders into a single JSON file
(`src/data/dashboard.json`), so the deployed page has NO runtime dependency
on this machine or on the live API:

- the agent's paper portfolio (from ../agent/state/portfolio.json),
- the latest decision pass, with the agent's written reasons,
- the NAV-live watchlist, fetched live from the Coinbase Tokenized Stocks
  API via the hardened client in ../api/ (falls back to the portfolio's
  seeded reference prices if the API is unreachable at build time),
- the latest daily brief (../briefs/*.md) as raw markdown,
- the AgentLog onchain status (deployment file if present, else the
  queued-decision count from ../agent/state/pending_onchain.json).

Run directly, or via `npm run data` / `npm run build` in dashboard/.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASHBOARD = HERE.parent
REPO = DASHBOARD.parent
OUT = DASHBOARD / "src" / "data" / "dashboard.json"

sys.path.insert(0, str(REPO))
from api import tokenized_stocks as ts  # noqa: E402


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def build_watchlist(portfolio: dict) -> dict:
    """NAV-live names with staleness, live from the API if possible."""
    now = datetime.now(timezone.utc)
    items: list[dict] = []
    source = "live"
    catalog_records = None
    try:
        stocks = ts.list_stocks()
        catalog_records = len(stocks)
        live = ts.nav_live_stocks(stocks)
        for s in sorted(live, key=lambda x: x["symbol"]):
            age = ts.nav_age_seconds(s, now=now)
            items.append(
                {
                    "symbol": s["symbol"],
                    "name": s.get("name") or s["symbol"],
                    "nav": s.get("nav_price"),
                    "nav_updated_at": s.get("nav_price_updated_at"),
                    "age_hours": round(age / 3600, 1) if age is not None else None,
                    "stale": ts.is_nav_stale(s, now=now),
                    "multiplier": s.get("multiplier"),
                    "contract_address": s.get("contract_address"),
                }
            )
    except Exception as exc:  # API unreachable at build time: use seeded refs
        source = f"fallback (API error: {exc.__class__.__name__})"
        refs = portfolio.get("references", {})
        for symbol in sorted(refs):
            ref = refs[symbol]
            updated = ts.parse_ts(ref.get("nav_updated_at"))
            age = (now - updated).total_seconds() if updated else None
            items.append(
                {
                    "symbol": symbol,
                    "name": symbol,
                    "nav": ref.get("nav"),
                    "nav_updated_at": ref.get("nav_updated_at"),
                    "age_hours": round(age / 3600, 1) if age is not None else None,
                    "stale": age is None or age > ts.DEFAULT_STALE_AFTER_SECONDS,
                    "multiplier": None,
                    "contract_address": None,
                }
            )
    stale_count = sum(1 for i in items if i["stale"])
    return {
        "source": source,
        "fetched_at": now.isoformat(),
        "catalog_records": catalog_records,
        "count": len(items),
        "stale_count": stale_count,
        "all_stale": bool(items) and stale_count == len(items),
        "items": items,
    }


def main() -> None:
    portfolio = _load_json(REPO / "agent" / "state" / "portfolio.json", {})
    pending = _load_json(REPO / "agent" / "state" / "pending_onchain.json", [])
    deployment = _load_json(REPO / "contracts" / "deployment.json", None)

    watchlist = build_watchlist(portfolio)
    nav_by_symbol = {i["symbol"]: i["nav"] for i in watchlist["items"]}

    positions = []
    positions_value = 0.0
    for ticker, pos in sorted(portfolio.get("positions", {}).items()):
        nav = nav_by_symbol.get(ticker) or pos.get("avg_nav") or 0
        value = pos.get("value_usd")
        if value is None:
            value = round(float(pos.get("qty_tokens", 0)) * float(nav), 2)
        positions_value += float(value)
        positions.append(
            {
                "ticker": ticker,
                "qty_tokens": pos.get("qty_tokens"),
                "qty_share_equiv": pos.get("qty_share_equiv"),
                "avg_nav": pos.get("avg_nav"),
                "current_nav": nav,
                "value_usd": value,
            }
        )

    cash = float(portfolio.get("cash", 0))
    history = portfolio.get("decision_history", [])
    latest_run = max((d.get("run", 0) for d in history), default=0)
    latest_decisions = [d for d in history if d.get("run", 0) == latest_run]

    brief_files = sorted((REPO / "briefs").glob("*.md"))
    brief = None
    if brief_files:
        latest = brief_files[-1]
        brief = {"file": latest.name, "markdown": latest.read_text()}

    if deployment and deployment.get("address"):
        onchain = {
            "deployed": True,
            "address": deployment["address"],
            "chain": deployment.get("chain", "Base Sepolia"),
            "explorer_url": f"https://sepolia.basescan.org/address/{deployment['address']}",
            "queued_count": 0,
        }
    else:
        onchain = {
            "deployed": False,
            "address": None,
            "chain": "Base Sepolia",
            "explorer_url": "https://sepolia.basescan.org",
            "queued_count": len(pending),
        }

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio": {
            "virtual_capital_usd": portfolio.get("virtual_capital_usd"),
            "cash": cash,
            "positions": positions,
            "positions_value": round(positions_value, 2),
            "total_value": round(cash + positions_value, 2),
            "runs": portfolio.get("runs", 0),
            "updated_at": portfolio.get("updated_at"),
        },
        "decisions": {
            "run": latest_run,
            "count": len(latest_decisions),
            "items": latest_decisions,
        },
        "watchlist": watchlist,
        "brief": brief,
        "onchain": onchain,
        "links": {
            "github": "https://github.com/rjrajput-web3/stocksage",
            "api": "https://api.coinbase.com/v1/tokenized-stocks",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2))
    print(
        f"dashboard data baked -> {OUT}\n"
        f"  watchlist: {watchlist['count']} names ({watchlist['source']}), "
        f"{watchlist['stale_count']} stale\n"
        f"  portfolio: cash ${cash:,.2f}, positions {len(positions)}, "
        f"total ${data['portfolio']['total_value']:,.2f}\n"
        f"  decisions: run {latest_run}, {len(latest_decisions)} items\n"
        f"  brief: {brief['file'] if brief else 'none'} | "
        f"onchain deployed: {onchain['deployed']}, queued: {onchain['queued_count']}"
    )


if __name__ == "__main__":
    main()
