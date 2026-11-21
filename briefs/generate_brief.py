#!/usr/bin/env python3
"""
StockSage Brief generator v0.

Pulls the NAV-live tokenized stocks from the hardened API client and writes
a dated, plain-language markdown brief. Research and education only — the
brief reports reference NAV values and timestamps; it never gives buy/sell
advice and never presents NAV as an executable price.

Honesty rules baked in:
- Every price is printed with the exact time it was last updated.
- If prices are stale (NAV feeds run 24/5 and hold the last close over the
  weekend), the brief says so at the top instead of pretending the numbers
  are live.
- A dated snapshot JSON is saved next to the brief so future briefs can
  compute real day-over-day moves instead of inventing them.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "api"))

from tokenized_stocks import (  # noqa: E402
    is_nav_stale,
    list_stocks,
    nav_age_seconds,
    nav_live_stocks,
)

# One plain-language line per known name: what the token tracks, no advice.
PLAIN = {
    "AAPLc": "Tracks Apple — the iPhone maker's stock, in token form.",
    "AMZNc": "Tracks Amazon — online shopping plus the AWS cloud business.",
    "ANTc": "Tracks Anthropic — the AI company behind Claude; a rare pre-IPO name in this catalog.",
    "CRCLc": "Tracks Circle — the company behind the USDC stablecoin.",
    "GOOGLc": "Tracks Alphabet — Google's parent: search, YouTube and cloud.",
    "INTCc": "Tracks Intel — the long-running chip maker.",
    "METAc": "Tracks Meta — Facebook, Instagram and WhatsApp's parent company.",
    "MSFTc": "Tracks Microsoft — Windows, Office, Azure cloud and a big AI bet.",
    "MSTRc": "Tracks MicroStrategy — a software company famous for holding a huge bitcoin treasury.",
    "NVDAc": "Tracks NVIDIA — the chip company at the center of the AI boom.",
    "SNDKc": "Tracks SanDisk — flash-memory storage. Note its multiplier is 8: one token unit represents 8 share-units after a corporate action, which is why its NAV number looks large.",
    "SPCXc": "Tracks SpaceX — rockets and Starlink, another pre-IPO name in token form.",
    "TSLAc": "Tracks Tesla — electric cars, energy storage and robots.",
}


def fmt_age(seconds: float | None) -> str:
    if seconds is None:
        return "no update timestamp published"
    h = seconds / 3600
    if h < 1:
        return f"{seconds / 60:.0f} minutes old"
    if h < 48:
        return f"{h:.1f} hours old"
    return f"{h / 24:.1f} days old"


def main() -> Path:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))  # briefs are dated on IST, the project's home timezone
    date_str = now.strftime("%Y-%m-%d")

    stocks = list_stocks()
    live = sorted(nav_live_stocks(stocks), key=lambda s: s["symbol"])

    # Save the raw snapshot so tomorrow's brief can compute real moves.
    snap_dir = HERE / "data"
    snap_dir.mkdir(exist_ok=True)
    snapshot = {
        "fetched_at": now.isoformat(),
        "records": len(stocks),
        "nav_live": {
            s["symbol"]: {
                "nav_price": s.get("nav_price"),
                "nav_price_updated_at": s.get("nav_price_updated_at"),
                "multiplier": s.get("multiplier"),
                "total_supply": s.get("total_supply"),
            }
            for s in live
        },
    }
    (snap_dir / f"snapshot-{date_str}.json").write_text(json.dumps(snapshot, indent=2))

    stale = [s for s in live if is_nav_stale(s)]
    lines: list[str] = []
    lines.append(f"# StockSage Brief — {date_str}")
    lines.append("")
    lines.append(
        "A plain-language look at Coinbase's tokenized stocks on Base. "
        "Research and education only — not financial advice. Prices below are "
        "NAV *reference* values from the Tokenized Stocks API, not live "
        "buy/sell quotes."
    )
    lines.append("")
    if stale:
        newest = min(nav_age_seconds(s) or 0 for s in live)
        lines.append(
            f"> **Stale-price note:** the NAV feeds behind these tokens run 24/5. "
            f"Right now {len(stale)} of {len(live)} prices are older than 6 hours "
            f"(the freshest is {fmt_age(newest)}), which is normal outside market "
            f"hours — on weekends these are simply the last closing reference "
            f"values, held until the feeds resume. Treat them as Friday's "
            f"scoreboard, not a live market."
        )
        lines.append("")
    lines.append(
        f"The full catalog lists {len(stocks)} token records; "
        f"{len(live)} currently publish a NAV reference price. Those are the "
        f"names this brief covers."
    )
    lines.append("")
    lines.append("## The NAV-live names")
    lines.append("")
    lines.append("| Token | What it tracks | NAV reference | Price last updated |")
    lines.append("|---|---|---:|---|")
    for s in live:
        lines.append(
            f"| {s['symbol']} | {s.get('name', '')} | ${s['nav_price']} | "
            f"{s.get('nav_price_updated_at')} ({fmt_age(nav_age_seconds(s))}) |"
        )
    lines.append("")
    lines.append("## In plain language")
    lines.append("")
    for s in live:
        sym = s["symbol"]
        one = PLAIN.get(sym, f"Tracks {s.get('name', sym)}.")
        mult = s.get("multiplier")
        mult_note = ""
        if mult not in (None, 1, 1.0) and "multiplier" not in one:
            mult_disp = f"{mult:.4f}".rstrip("0").rstrip(".")
            mult_note = f" Its multiplier is {mult_disp}, so token units and share units are not exactly 1:1."
        lines.append(f"- **{sym} — ${s['nav_price']}** ({fmt_age(nav_age_seconds(s))}). {one}{mult_note}")
    lines.append("")
    lines.append(
        "## What to watch next\n\nWhen the feeds resume, this brief's saved "
        "snapshot lets the next edition report real moves against today's "
        "reference values instead of guesses.\n\n---\n"
        "*Generated by StockSage from the public Coinbase Tokenized Stocks API. "
        "Simulated, educational content only.*"
    )

    out = HERE / f"{date_str}.md"
    out.write_text("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    p = main()
    print(f"wrote {p}")
