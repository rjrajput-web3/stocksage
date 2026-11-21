// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {AgentLog} from "../src/AgentLog.sol";

/// Deploy AgentLog. Usage (via deploy.sh, which loads the key from
/// ../../.deployer.env — never commit that file):
///   forge script script/Deploy.s.sol --rpc-url $BASE_SEPOLIA_RPC \
///     --private-key $DEPLOYER_PRIVATE_KEY --broadcast
contract Deploy is Script {
    function run() external returns (AgentLog deployed) {
        vm.startBroadcast();
        deployed = new AgentLog();
        vm.stopBroadcast();
    }
}
