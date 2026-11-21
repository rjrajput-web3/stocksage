"""StockSage paper portfolio — JSON state, no real assets, ever.

State lives in agent/state/portfolio.json:

  cash               virtual dollars not yet allocated (starts at $100,000)
  positions          {ticker: {qty_tokens, qty_share_equiv, avg_nav,
                               multiplier, value_usd}}
  references         {ticker: {nav, nav_updated_at, seeded_from}} — the
                     trailing reference each run measures moves against;
                     rolls forward to the latest observation after a run
  decision_history   every decision ever taken, with its written reason
  runs               number of completed decision passes

Quantities: the simulated position is denominated in token units bought at
the NAV reference price (qty_tokens = usd / nav). qty_share_equiv applies
the token's published multiplier (token units x multiplier = share
equivalents), which is how the underlying catalog expresses corporate
actions such as splits and dividends. Position value is marked at the
latest observed NAV each run.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .engine import VIRTUAL_CAPITAL_USD

STATE_PATH = Path(__file__).resolve().parent / "state" / "portfolio.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fresh_state() -> dict:
    return {
        "virtual_capital_usd": VIRTUAL_CAPITAL_USD,
        "cash": VIRTUAL_CAPITAL_USD,
        "positions": {},
        "references": {},
        "decision_history": [],
        "runs": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def load_state(path: Path = STATE_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return fresh_state()


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    path.write_text(json.dumps(state, indent=2) + "\n")


def apply_decisions(state: dict, decisions: list[dict], observations: list[dict]) -> dict:
    """Apply one pass: execute SIM_BUYs, re-mark positions, roll references."""
    obs_by_ticker = {o["ticker"]: o for o in observations}
    positions = state.setdefault("positions", {})

    for d in decisions:
        ticker = d["ticker"]
        if d["side"] == "SIM_BUY" and d.get("usd_amount", 0) > 0:
            nav = float(d["nav_price"])
            mult = float(obs_by_ticker.get(ticker, {}).get("multiplier", 1) or 1)
            qty = d["usd_amount"] / nav
            pos = positions.setdefault(
                ticker,
                {"qty_tokens": 0.0, "qty_share_equiv": 0.0, "avg_nav": nav,
                 "multiplier": mult, "value_usd": 0.0},
            )
            old_qty = float(pos["qty_tokens"])
            new_qty = old_qty + qty
            pos["avg_nav"] = (
                (float(pos["avg_nav"]) * old_qty + nav * qty) / new_qty if new_qty else nav
            )
            pos["qty_tokens"] = new_qty
            pos["multiplier"] = mult
            pos["qty_share_equiv"] = new_qty * mult
            state["cash"] = round(float(state["cash"]) - d["usd_amount"], 2)
        state.setdefault("decision_history", []).append(
            {
                "run": state.get("runs", 0) + 1,
                "ticker": ticker,
                "side": d["side"],
                "nav_price": d["nav_price"],
                "usd_amount": d.get("usd_amount", 0.0),
                "reason": d["reason"],
            }
        )

    # Re-mark every position at the latest observed NAV and roll references.
    for ticker, obs in obs_by_ticker.items():
        nav = float(obs["nav_price"])
        if ticker in positions:
            positions[ticker]["value_usd"] = round(
                float(positions[ticker]["qty_tokens"]) * nav, 2
            )
        state.setdefault("references", {})[ticker] = {
            "nav": nav,
            "nav_updated_at": obs.get("nav_price_updated_at"),
            "seeded_from": obs.get("source", "live"),
        }

    state["runs"] = state.get("runs", 0) + 1
    return state


def portfolio_value(state: dict) -> float:
    return round(
        float(state.get("cash", 0.0))
        + sum(float(p.get("value_usd", 0.0)) for p in state.get("positions", {}).values()),
        2,
    )
