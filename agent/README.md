# agent/

The StockSage strategy engine and simulated portfolio live here (build day
Nov 23). Published rule set first, code second: the agent only ever acts on
NAV-live names, never on stale prices, and every simulated decision it makes
is written to the AgentLog contract with a hash of its written reasoning.
