# StockSage — Published Rules for the Simulated Portfolio

These are the exact rules the StockSage agent follows. They are fixed in
advance, applied mechanically, and never adjusted after the fact to make the
history look better. Anyone can re-run the engine on the same price data and
get the same decisions.

**What this is:** a research and education experiment. StockSage runs a
*simulated* (paper) portfolio over the tokenized stocks that publish a live
NAV reference price on Base, so readers can watch how a simple, transparent
rule set behaves. It is not financial advice, it does not trade anything, and
no real money or real securities are involved at any point.

## The rules

1. **Working set.** The agent only considers the names that currently
   publish a NAV price (today: 13). A name with no NAV is never acted on.
2. **Freshness gate.** NAV feeds run on market hours (24/5). If a name's NAV
   is more than 6 hours old — a weekend hold, a holiday, a frozen feed —
   the agent takes no action on that name that run. Stale prices are
   labelled, never silently traded on.
3. **Virtual capital.** The simulated portfolio starts with **$100,000** of
   imaginary cash. All amounts below are in those virtual dollars.
4. **Trailing reference.** Each name has a trailing reference NAV: the NAV
   observed on the previous run (the first run is seeded from the
   2026-11-22 snapshot). Each run measures the percentage move from that
   reference to the current NAV, then the reference rolls forward.
5. **Momentum band (enter / add).** If a name's NAV has moved **up 1.5% or
   more** versus its trailing reference, the agent records a simulated buy
   of one step ($5,000) in that name.
6. **Mean-reversion band (add on a dip).** If a name's NAV has moved **down
   2.0% or more** versus its trailing reference, the agent records a
   simulated buy of one step ($5,000) in that name — the rule set's way of
   leaning against a sharp move rather than chasing it.
7. **Position cap.** No single name may exceed **$10,000** (10% of virtual
   capital) in simulated holdings. A buy that would cross the cap is
   reduced to the remaining room, or skipped if there is none.
8. **Exposure cap.** Total simulated holdings may not exceed **$60,000**
   (60% of virtual capital); at least 40% always stays as virtual cash.
9. **One pass per run.** Each run makes at most one decision per name, in
   alphabetical order, so a run's outcome never depends on ordering luck.
10. **Everything is logged.** Every decision — buys and holds alike — is
    written to the public AgentLog contract on Base Sepolia with a hash of
    its written reason (queued locally until the log contract is deployed).
    Holds are logged too: "did nothing, and here is why" is part of the
    record.

**Deliberately out of scope for this first published version:** sell/exit
rules, leverage, shorting, and any use of prices other than the published
NAV reference. The NAV is a reference value, not an executable bid/ask —
the simulation says so wherever it reports a price.
