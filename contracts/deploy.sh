#!/usr/bin/env bash
# Deploy AgentLog to Base Sepolia and record the deployment.
#
# Prereqs:
#   1. ~/.foundry/bin on PATH (forge + cast).
#   2. ../../.deployer.env exists (chmod 600) with DEPLOYER_PRIVATE_KEY set.
#   3. The deployer wallet holds a little Base Sepolia ETH (testnet faucet).
#
# The script verifies the deployment by reading count() back from the
# deployed contract, then writes contracts/deployment.json.
set -euo pipefail

export PATH="$HOME/.foundry/bin:$PATH"
cd "$(dirname "$0")"

ENV_FILE="../../.deployer.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE (deployer key file)" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
RPC="${BASE_SEPOLIA_RPC:-https://sepolia.base.org}"

BAL="$(cast balance --rpc-url "$RPC" "$DEPLOYER_ADDRESS")"
echo "deployer $DEPLOYER_ADDRESS balance: $BAL wei"
if [[ "$BAL" == "0" ]]; then
  echo "deployer has no Base Sepolia ETH yet — fund it from a faucet first" >&2
  exit 1
fi

OUT="$(forge create src/AgentLog.sol:AgentLog \
  --rpc-url "$RPC" \
  --private-key "$DEPLOYER_PRIVATE_KEY" \
  --broadcast)"
echo "$OUT"
ADDR="$(echo "$OUT" | grep -i 'Deployed to:' | awk '{print $3}')"
TX="$(echo "$OUT" | grep -i 'Transaction hash:' | awk '{print $3}')"

COUNT="$(cast call --rpc-url "$RPC" "$ADDR" 'count()(uint256)')"
echo "verified: AgentLog.count() = $COUNT"

cat > deployment.json <<EOF
{
  "contract": "AgentLog",
  "chain": "base-sepolia",
  "chain_id": 84532,
  "address": "$ADDR",
  "tx_hash": "$TX",
  "deployer": "$DEPLOYER_ADDRESS",
  "verified_count": $COUNT
}
EOF
echo "wrote deployment.json for $ADDR"
