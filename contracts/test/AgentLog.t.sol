// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {AgentLog} from "../src/AgentLog.sol";

contract AgentLogTest is Test {
    AgentLog internal agentLog;

    function setUp() public {
        agentLog = new AgentLog();
    }

    function test_WriteAndReadBackTwoRecords() public {
        bytes32 reason1 = keccak256("momentum band entry, NAV fresh");
        bytes32 reason2 = keccak256("mean-reversion exit, NAV stale-flagged");

        uint256 i0 = agentLog.recordDecision("NVDAc", "SIM_BUY", 12982480034, reason1);
        uint256 i1 = agentLog.recordDecision("TSLAc", "SIM_SELL", 35045000000, reason2);

        assertEq(i0, 0);
        assertEq(i1, 1);
        assertEq(agentLog.count(), 2);

        AgentLog.Record memory r0 = agentLog.getRecord(0);
        assertEq(r0.ticker, "NVDAc");
        assertEq(r0.side, "SIM_BUY");
        assertEq(r0.navPrice, 12982480034);
        assertEq(r0.reasonHash, reason1);
        assertEq(r0.index, 0);
        assertEq(r0.timestamp, block.timestamp);

        AgentLog.Record memory r1 = agentLog.getRecord(1);
        assertEq(r1.ticker, "TSLAc");
        assertEq(r1.side, "SIM_SELL");
        assertEq(r1.navPrice, 35045000000);
        assertEq(r1.reasonHash, reason2);
        assertEq(r1.index, 1);
    }

    function test_GetRecordOutOfRangeReverts() public {
        vm.expectRevert("AgentLog: index out of range");
        agentLog.getRecord(0);
    }
}
