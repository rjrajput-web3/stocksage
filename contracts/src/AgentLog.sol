// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AgentLog — append-only onchain log of StockSage agent decisions.
/// @notice Every simulated-portfolio decision the StockSage agent makes is
///         recorded here (ticker, side, NAV reference price at decision time,
///         and a hash of the written reasoning) so anyone can verify what the
///         agent did and when. The log is append-only: records can never be
///         edited or deleted, there are no admin functions, and the contract
///         holds no value and moves no assets. Research/education tooling only.
contract AgentLog {
    struct Record {
        uint256 timestamp;
        string ticker;
        string side; // e.g. "SIM_BUY" / "SIM_SELL" / "HOLD" — simulated only
        uint256 navPrice; // NAV reference price, scaled by 1e8
        bytes32 reasonHash; // keccak256 of the agent's written reasoning
        uint256 index;
    }

    Record[] private _records;

    event DecisionRecorded(
        uint256 indexed index,
        string ticker,
        string side,
        uint256 navPrice,
        bytes32 reasonHash,
        uint256 timestamp
    );

    /// @notice Append a decision record. Anyone may write; records are
    ///         immutable once written, so the log stays a neutral public
    ///         diary rather than a curated feed.
    function recordDecision(
        string calldata ticker,
        string calldata side,
        uint256 navPrice,
        bytes32 reasonHash
    ) external returns (uint256 index) {
        index = _records.length;
        _records.push(
            Record({
                timestamp: block.timestamp,
                ticker: ticker,
                side: side,
                navPrice: navPrice,
                reasonHash: reasonHash,
                index: index
            })
        );
        emit DecisionRecorded(index, ticker, side, navPrice, reasonHash, block.timestamp);
    }

    /// @notice Total number of decision records written so far.
    function count() external view returns (uint256) {
        return _records.length;
    }

    /// @notice Read back the record at index `i`.
    function getRecord(uint256 i) external view returns (Record memory) {
        require(i < _records.length, "AgentLog: index out of range");
        return _records[i];
    }
}
