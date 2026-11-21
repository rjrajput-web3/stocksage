"""StockSage runner — one decision pass, state update, onchain logging hook.

Usage (from the stocksage/ directory):

    python3 -m agent.run

What one run does:
  1. Fetches the live NAV-live set from the tokenized-stocks API.
  2. Loads the paper portfolio state (agent/state/portfolio.json). On the
     very first run, trailing references are seeded from the saved snapshot
     briefs/data/snapshot-2026-11-22.json; afterwards they come from state.
  3. Runs one deterministic decision pass under the published rules
     (agent/RULES.md, agent/engine.py) and applies it to the state.
  4. Tries to anchor the decisions onchain: if contracts/deployment.json
     names an AgentLog contract, each decision is written to it; if the
     deployer wallet has been funded but nothing is deployed yet, the
     deploy script runs first. Otherwise the decisions are queued in
     agent/state/pending_onchain.json for later logging.
  5. Prints a plain-language summary of the pass.

Research/education simulation only: virtual money, reference prices, no
real assets, nothing here is financial advice.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.tokenized_stocks import is_nav_stale, nav_age_seconds, nav_live_stocks  # noqa: E402
from agent import engine, portfolio  # noqa: E402

SNAPSHOT_PATH = ROOT / "briefs" / "data" / "snapshot-2026-11-22.json"
DEPLOYMENT_PATH = ROOT / "contracts" / "deployment.json"
PENDING_PATH = ROOT / "agent" / "state" / "pending_onchain.json"
DEPLOYER_ENV = ROOT.parent / ".deployer.env"
BASE_SEPOLIA_RPC = "https://sepolia.base.org"


def keccak256_hex(text: str) -> str:
    """Ethereum Keccak-256 of a string, as 0x-prefixed hex."""
    try:
        import sha3  # pysha3: true Keccak-256

        return "0x" + sha3.keccak_256(text.encode()).hexdigest()
    except ImportError:
        out = subprocess.run(
            ["cast", "keccak", text], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()


def build_observations() -> list[dict]:
    obs = []
    for s in nav_live_stocks():
        age = nav_age_seconds(s)
        obs.append(
            {
                "ticker": s["symbol"],
                "nav_price": float(s["nav_price"]),
                "nav_price_updated_at": s.get("nav_price_updated_at"),
                "nav_age_hours": (age / 3600.0) if age is not None else None,
                "is_stale": is_nav_stale(s),
                "multiplier": float(s.get("multiplier", 1) or 1),
                "source": "live",
            }
        )
    return obs


def seed_references_from_snapshot() -> dict:
    if not SNAPSHOT_PATH.exists():
        return {}
    snap = json.loads(SNAPSHOT_PATH.read_text())
    return {
        ticker: float(rec["nav_price"])
        for ticker, rec in snap.get("nav_live", {}).items()
    }


def _read_deployer_env() -> dict:
    env = {}
    if DEPLOYER_ENV.exists():
        for line in DEPLOYER_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _deployer_balance_wei(address: str) -> int:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance",
         "params": [address, "latest"]}
    ).encode()
    req = urllib.request.Request(
        BASE_SEPOLIA_RPC,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "stocksage-agent/0.1"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return int(json.loads(resp.read())["result"], 16)


def _log_onchain(contract: str, decisions: list[dict], deployer_key: str) -> list[str]:
    """Write each decision to AgentLog via cast send. Returns tx hashes."""
    txs = []
    env = dict(os.environ, PATH=os.path.expanduser("~/.foundry/bin") + ":" + os.environ["PATH"])
    for d in decisions:
        nav_scaled = int(round(float(d["nav_price"]) * 1e8))
        reason_hash = keccak256_hex(d["reason"])
        out = subprocess.run(
            [
                "cast", "send", "--rpc-url", BASE_SEPOLIA_RPC,
                "--private-key", deployer_key,
                contract,
                "recordDecision(string,string,uint256,bytes32)",
                d["ticker"], d["side"], str(nav_scaled), reason_hash,
            ],
            capture_output=True, text=True, env=env, check=True,
        )
        tx_hash = ""
        for line in out.stdout.splitlines():
            if line.strip().startswith("transactionHash"):
                tx_hash = line.split()[-1]
        txs.append(tx_hash)
    return txs


def anchor_decisions(decisions: list[dict]) -> str:
    """Onchain logging hook. Returns a one-line status for the summary."""
    deployer = _read_deployer_env()
    address = deployer.get("DEPLOYER_ADDRESS", "")
    key = deployer.get("DEPLOYER_PRIVATE_KEY", "")

    deployment = None
    if DEPLOYMENT_PATH.exists():
        deployment = json.loads(DEPLOYMENT_PATH.read_text())

    if deployment is None and address:
        try:
            balance = _deployer_balance_wei(address)
        except Exception as exc:  # RPC hiccup: queue instead of crashing
            balance = 0
            print(f"  (balance check failed: {exc}; treating deployer as unfunded)")
        if balance > int(0.01e18):
            print(f"  deployer funded ({balance / 1e18:.4f} ETH) — deploying AgentLog...")
            env = dict(os.environ, PATH=os.path.expanduser("~/.foundry/bin") + ":" + os.environ["PATH"])
            subprocess.run(
                ["bash", str(ROOT / "contracts" / "deploy.sh")],
                check=True, env=env, capture_output=True, text=True,
            )
            if DEPLOYMENT_PATH.exists():
                deployment = json.loads(DEPLOYMENT_PATH.read_text())

    if deployment is not None:
        txs = _log_onchain(deployment["address"], decisions, key)
        return (
            f"onchain: {len(txs)} decision(s) written to AgentLog "
            f"{deployment['address']} on Base Sepolia"
        )

    # Not deployed yet: queue every decision for later logging.
    queue = []
    if PENDING_PATH.exists():
        queue = json.loads(PENDING_PATH.read_text())
    run_ts = datetime.now(timezone.utc).isoformat()
    for d in decisions:
        queue.append(
            {
                "queued_at": run_ts,
                "ticker": d["ticker"],
                "side": d["side"],
                "nav_price": d["nav_price"],
                "nav_price_scaled_1e8": int(round(float(d["nav_price"]) * 1e8)),
                "usd_amount": d.get("usd_amount", 0.0),
                "reason": d["reason"],
                "reason_hash": keccak256_hex(d["reason"]),
            }
        )
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(json.dumps(queue, indent=2) + "\n")
    return (
        f"onchain: AgentLog not deployed yet (deployer unfunded) — "
        f"{len(decisions)} decision(s) queued in agent/state/pending_onchain.json "
        f"({len(queue)} total queued)"
    )


def main() -> int:
    observations = build_observations()
    state = portfolio.load_state()

    if state.get("references"):
        references = {t: float(r["nav"]) for t, r in state["references"].items()}
        ref_source = "portfolio state (previous run)"
    else:
        references = seed_references_from_snapshot()
        ref_source = "snapshot-2026-11-22.json (first run seed)"

    decisions = engine.run_pass(observations, references, state)
    state = portfolio.apply_decisions(state, decisions, observations)
    portfolio.save_state(state)

    buys = [d for d in decisions if d["side"] == "SIM_BUY"]
    holds = [d for d in decisions if d["side"] == "HOLD"]
    stale = [o for o in observations if o["is_stale"]]

    print("=" * 68)
    print(f"StockSage decision pass #{state['runs']} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    print(f"Working set: {len(observations)} NAV-live names | references: {ref_source}")
    print(f"Stale NAVs this run: {len(stale)} of {len(observations)} "
          f"(feeds hold the last close outside market hours)")
    print("-" * 68)
    for d in decisions:
        amt = f" ${d['usd_amount']:,.2f}" if d["side"] == "SIM_BUY" else ""
        print(f"{d['ticker']:<7} {d['side']:<8}{amt:<12} NAV ${d['nav_price']:,.2f}")
        print(f"        {d['reason']}")
    print("-" * 68)
    print(f"Decisions: {len(buys)} simulated buy(s), {len(holds)} hold(s)")
    print(f"Cash: ${state['cash']:,.2f} | Positions: {len(state['positions'])} | "
          f"Portfolio value (marked at NAV): ${portfolio.portfolio_value(state):,.2f}")
    print(anchor_decisions(decisions))
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
