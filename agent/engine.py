"""StockSage strategy engine — deterministic, published rules, paper only.

The engine implements exactly the rule set published in agent/RULES.md:

  * working set   = names that currently publish a NAV reference price
  * freshness     = a NAV older than 6 hours is never acted on (HOLD, with
                    the staleness stated in the reason)
  * capital       = $100,000 virtual; one step = $5,000 per decision
  * momentum band = NAV up >= +1.5% vs the trailing reference -> SIM_BUY
  * mean-reversion band = NAV down <= -2.0% vs the trailing reference
                    -> SIM_BUY (lean against the dip)
  * caps          = $10,000 max per name, $60,000 max total exposure
  * one decision per name per run, names processed alphabetically

Every decision is a dict: {ticker, side, nav_price, reason}. "side" is
"SIM_BUY" or "HOLD" (this first published version has no exit rule — see
RULES.md). The engine is pure: it takes observations + portfolio state and
returns decisions without doing any I/O, so the same inputs always produce
the same decisions.

This is a research/education simulation. Nothing here is financial advice;
the NAV is a reference value, not an executable price, and no real assets
are involved.
"""

from __future__ import annotations

VIRTUAL_CAPITAL_USD = 100_000.0
STEP_USD = 5_000.0
MAX_POSITION_USD = 10_000.0
MAX_TOTAL_EXPOSURE_USD = 60_000.0
MOMENTUM_ENTER_PCT = 1.5
MEAN_REVERSION_DIP_PCT = -2.0


def decide(
    *,
    ticker: str,
    nav_price: float,
    reference_nav: float | None,
    nav_age_hours: float | None,
    is_stale: bool,
    position_value_usd: float,
    total_exposure_usd: float,
    cash_usd: float,
) -> dict:
    """One deterministic decision for one name. See module docstring."""
    base = {"ticker": ticker, "nav_price": nav_price}

    if reference_nav is None or reference_nav <= 0:
        return {
            **base,
            "side": "HOLD",
            "usd_amount": 0.0,
            "reason": (
                f"No trailing reference NAV for {ticker} yet, so there is no "
                "measured move to act on; reference seeded this run."
            ),
        }

    change_pct = (nav_price / reference_nav - 1.0) * 100.0

    if is_stale:
        age_txt = f"{nav_age_hours:.1f}h old" if nav_age_hours is not None else "of unknown age"
        return {
            **base,
            "side": "HOLD",
            "usd_amount": 0.0,
            "reason": (
                f"NAV feed for {ticker} is {age_txt} (stale; feeds hold the "
                f"last close outside market hours). Published rules require a "
                f"fresh NAV before any simulated trade. Move vs trailing "
                f"reference is {change_pct:+.2f}% in the held price."
            ),
        }

    if change_pct >= MOMENTUM_ENTER_PCT:
        band, rule = "momentum", f"up {change_pct:+.2f}% vs trailing reference (band: >= +{MOMENTUM_ENTER_PCT}%)"
    elif change_pct <= MEAN_REVERSION_DIP_PCT:
        band, rule = "mean-reversion", f"down {change_pct:+.2f}% vs trailing reference (band: <= {MEAN_REVERSION_DIP_PCT}%)"
    else:
        return {
            **base,
            "side": "HOLD",
            "usd_amount": 0.0,
            "reason": (
                f"NAV move of {change_pct:+.2f}% vs trailing reference sits "
                f"inside the published bands (+{MOMENTUM_ENTER_PCT}% / "
                f"{MEAN_REVERSION_DIP_PCT}%); no action."
            ),
        }

    # A band was crossed: size the step against the published caps.
    room_position = MAX_POSITION_USD - position_value_usd
    room_exposure = MAX_TOTAL_EXPOSURE_USD - total_exposure_usd
    usd = min(STEP_USD, room_position, room_exposure, cash_usd)
    if usd <= 0:
        return {
            **base,
            "side": "HOLD",
            "usd_amount": 0.0,
            "reason": (
                f"{band.capitalize()} band crossed ({rule}), but the "
                f"published caps leave no room (position ${position_value_usd:,.0f} "
                f"of ${MAX_POSITION_USD:,.0f}, exposure ${total_exposure_usd:,.0f} "
                f"of ${MAX_TOTAL_EXPOSURE_USD:,.0f}, cash ${cash_usd:,.0f}); no action."
            ),
        }
    return {
        **base,
        "side": "SIM_BUY",
        "usd_amount": round(usd, 2),
        "reason": (
            f"{band.capitalize()} rule: NAV {rule}. Simulated buy of "
            f"${usd:,.2f} at the NAV reference price (not an executable price)."
        ),
    }


def run_pass(observations: list[dict], references: dict, portfolio: dict) -> list[dict]:
    """One full decision pass over all observations, alphabetically.

    observations: [{ticker, nav_price, nav_age_hours, is_stale, multiplier}]
    references:   {ticker: reference_nav}
    portfolio:    the state dict managed by agent.portfolio
    """
    positions = portfolio.get("positions", {})
    cash = float(portfolio.get("cash", VIRTUAL_CAPITAL_USD))
    exposure = sum(float(p.get("value_usd", 0.0)) for p in positions.values())

    decisions = []
    for obs in sorted(observations, key=lambda o: o["ticker"]):
        ticker = obs["ticker"]
        pos_value = float(positions.get(ticker, {}).get("value_usd", 0.0))
        d = decide(
            ticker=ticker,
            nav_price=float(obs["nav_price"]),
            reference_nav=references.get(ticker),
            nav_age_hours=obs.get("nav_age_hours"),
            is_stale=bool(obs.get("is_stale", True)),
            position_value_usd=pos_value,
            total_exposure_usd=exposure,
            cash_usd=cash,
        )
        decisions.append(d)
        if d["side"] == "SIM_BUY":
            cash -= d["usd_amount"]
            exposure += d["usd_amount"]
    return decisions
