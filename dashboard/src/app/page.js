import { marked } from "marked";
import data from "../data/dashboard.json";

const fmtUSD = (n, digits = 2) =>
  n == null
    ? "—"
    : "$" +
      Number(n).toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

const fmtNAV = (n) => {
  if (n == null) return "—";
  const v = Number(n);
  return "$" + v.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: v < 10 ? 4 : 2,
  });
};

const fmtDateTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    }) +
    ", " +
    d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }) +
    " UTC"
  );
};

function Logo() {
  return (
    <svg viewBox="0 0 48 48" width="46" height="46" aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7FA663" />
          <stop offset="1" stopColor="#44603A" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="44" height="44" rx="12" fill="url(#lg)" />
      <path
        d="M13.5 33.5 C13.5 20.5 21.5 12.5 34.5 12.5 C34.5 25.5 26.5 34.5 14.5 34.5 Z"
        fill="#0C110C"
        opacity="0.30"
      />
      <polyline
        points="12.5,31.5 19.5,25 24.5,28.5 35.5,16.5"
        fill="none"
        stroke="#EFF6E4"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="35.5" cy="16.5" r="2.7" fill="#EFF6E4" />
    </svg>
  );
}

function SideBadge({ side }) {
  const cls =
    side === "BUY"
      ? "badge badge-buy"
      : side === "SELL"
        ? "badge badge-sell"
        : "badge badge-hold";
  return <span className={cls}>{side}</span>;
}

export default function Page() {
  const { portfolio, decisions, watchlist, brief, onchain, links } = data;
  const briefHtml = brief ? marked.parse(brief.markdown) : null;
  const generated = fmtDateTime(data.generated_at);

  return (
    <div className="wrap">
      {/* ---------- header ---------- */}
      <header className="site-header">
        <div className="brand">
          <Logo />
          <div>
            <div className="name">StockSage</div>
            <div className="tag">Tokenized stocks on Base, explained plainly</div>
          </div>
        </div>
        <nav className="header-links">
          <a className="btn" href={links.github} target="_blank" rel="noreferrer">
            GitHub repo
          </a>
          <a className="btn" href="#brief">
            Latest brief
          </a>
          <a className="btn" href="#onchain">
            Onchain log
          </a>
        </nav>
      </header>

      {/* ---------- hero ---------- */}
      <div className="hero">
        <h1>
          An AI agent watching tokenized stocks, <span className="accent">in the open.</span>
        </h1>
        <p>
          StockSage follows the tokenized stocks that publish a live NAV reference
          price on Base, writes a plain-language brief, and runs a simulated
          portfolio under published rules — every decision recorded, with its
          reasoning, for anyone to check.
        </p>
        <span className="chip">Simulated portfolio. Not financial advice.</span>
      </div>

      {/* ---------- portfolio ---------- */}
      <section id="portfolio">
        <div className="section-head">
          <h2>Simulated portfolio</h2>
          <span className="sub">
            Paper portfolio · {portfolio.runs}{" "}
            {portfolio.runs === 1 ? "decision pass" : "decision passes"} so far ·
            updated {fmtDateTime(portfolio.updated_at)}
          </span>
        </div>
        <div className="grid-stats">
          <div className="card stat">
            <div className="label">Total value</div>
            <div className="value">{fmtUSD(portfolio.total_value)}</div>
            <div className="note">Virtual funds, never real money</div>
          </div>
          <div className="card stat">
            <div className="label">Cash</div>
            <div className="value">{fmtUSD(portfolio.cash)}</div>
            <div className="note">
              of {fmtUSD(portfolio.virtual_capital_usd, 0)} starting capital
            </div>
          </div>
          <div className="card stat">
            <div className="label">In positions</div>
            <div className="value">{fmtUSD(portfolio.positions_value)}</div>
            <div className="note">
              {portfolio.positions.length}{" "}
              {portfolio.positions.length === 1 ? "open position" : "open positions"}
            </div>
          </div>
          <div className="card stat">
            <div className="label">Names watched</div>
            <div className="value">{watchlist.count}</div>
            <div className="note">NAV-live of {watchlist.catalog_records ?? "—"} catalog records</div>
          </div>
        </div>

        <div className="card" style={{ marginTop: 14 }}>
          {portfolio.positions.length === 0 ? (
            <p className="empty">
              No open positions yet. In the latest pass the agent held every name:
              the NAV feeds were showing a held weekend close, and the published
              rules require a fresh price before any simulated trade. Doing
              nothing — and publishing why — is part of the record.
            </p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Token</th>
                    <th className="num">Token units</th>
                    <th className="num">Share equiv.</th>
                    <th className="num">Avg NAV</th>
                    <th className="num">Current NAV</th>
                    <th className="num">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((p) => (
                    <tr key={p.ticker}>
                      <td className="ticker">{p.ticker}</td>
                      <td className="num">{Number(p.qty_tokens).toFixed(4)}</td>
                      <td className="num">{Number(p.qty_share_equiv).toFixed(4)}</td>
                      <td className="num">{fmtNAV(p.avg_nav)}</td>
                      <td className="num">{fmtNAV(p.current_nav)}</td>
                      <td className="num">{fmtUSD(p.value_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* ---------- decisions ---------- */}
      <section id="decisions">
        <div className="section-head">
          <h2>Latest decision pass</h2>
          <span className="sub">
            Pass #{decisions.run} · {decisions.count} decisions, each with the
            agent&apos;s written reason
          </span>
        </div>
        <div className="card">
          {decisions.items.map((d) => (
            <div className="decision" key={d.ticker}>
              <div className="decision-top">
                <span className="ticker">{d.ticker}</span>
                <SideBadge side={d.side} />
                <span className="nav">
                  NAV at decision: {fmtNAV(d.nav_price)}
                  {d.usd_amount > 0 ? ` · amount ${fmtUSD(d.usd_amount)}` : ""}
                </span>
              </div>
              <p className="reason">{d.reason}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- watchlist ---------- */}
      <section id="watchlist">
        <div className="section-head">
          <h2>NAV-live watchlist</h2>
          <span className="sub">
            Reference prices from the Coinbase Tokenized Stocks API · fetched{" "}
            {fmtDateTime(watchlist.fetched_at)} · source: {watchlist.source}
          </span>
        </div>
        {watchlist.all_stale && (
          <div className="notice notice-amber">
            <span>
              <strong>Price held from Friday close.</strong> The NAV feeds behind
              these tokens run 24/5, so over the weekend every price below is the
              last closing reference value, held until the feeds resume. Treat
              them as Friday&apos;s scoreboard, not a live market.
            </span>
          </div>
        )}
        <div className="card">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Token</th>
                  <th>Tracks</th>
                  <th className="num">NAV reference</th>
                  <th>Price last updated</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.items.map((s) => (
                  <tr key={s.symbol}>
                    <td className="ticker">{s.symbol}</td>
                    <td className="company">{s.name}</td>
                    <td className="num">{fmtNAV(s.nav)}</td>
                    <td className="company">
                      {fmtDateTime(s.nav_updated_at)}
                      {s.age_hours != null ? ` (${s.age_hours}h old)` : ""}
                    </td>
                    <td>
                      {s.stale ? (
                        <span className="badge badge-stale">Held close</span>
                      ) : (
                        <span className="badge badge-fresh">Fresh</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="sub" style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 10 }}>
          NAV is a Chainlink-based reference value, not a live buy/sell quote and
          not an executable price. The full catalog lists{" "}
          {watchlist.catalog_records ?? "hundreds of"} token records; only these{" "}
          {watchlist.count} currently publish a NAV price.
        </p>
      </section>

      {/* ---------- brief ---------- */}
      {brief && (
        <section id="brief">
          <div className="section-head">
            <h2>Latest brief</h2>
            <span className="sub">
              {brief.file.replace(".md", "")} ·{" "}
              <a
                href={`${links.github}/blob/main/briefs/${brief.file}`}
                target="_blank"
                rel="noreferrer"
              >
                Read it in the repo
              </a>
            </span>
          </div>
          <div className="card brief-body" dangerouslySetInnerHTML={{ __html: briefHtml }} />
        </section>
      )}

      {/* ---------- onchain & links ---------- */}
      <section id="onchain">
        <div className="section-head">
          <h2>Onchain decision log</h2>
          <span className="sub">Every simulated decision, anchored for anyone to verify</span>
        </div>
        <div className="grid-2">
          <div className="card">
            <div className="kv">
              <span className="k">Contract</span>
              <span className="v">AgentLog</span>
            </div>
            <div className="kv">
              <span className="k">Network</span>
              <span className="v">{onchain.chain} (testnet)</span>
            </div>
            <div className="kv">
              <span className="k">Status</span>
              <span className="v">
                {onchain.deployed ? "Deployed" : "Not yet deployed"}
              </span>
            </div>
            <div className="kv">
              <span className="k">Decisions queued</span>
              <span className="v">{onchain.queued_count}</span>
            </div>
            {onchain.deployed ? (
              <div className="kv">
                <span className="k">Address</span>
                <span className="v">
                  <a href={onchain.explorer_url} target="_blank" rel="noreferrer">
                    {onchain.address.slice(0, 10)}…{onchain.address.slice(-6)}
                  </a>
                </span>
              </div>
            ) : (
              <p className="empty">
                The contract is written and tested. Deployment waits on Base
                Sepolia test funds for the deployer wallet; the moment it lands,
                the queued decisions are written onchain and the contract link
                appears here.{" "}
                <a href={onchain.explorer_url} target="_blank" rel="noreferrer">
                  Basescan (Sepolia)
                </a>
              </p>
            )}
          </div>
          <div className="card">
            <div className="kv">
              <span className="k">Source code</span>
              <span className="v">
                <a href={links.github} target="_blank" rel="noreferrer">
                  github.com/rjrajput-web3/stocksage
                </a>
              </span>
            </div>
            <div className="kv">
              <span className="k">Agent rules</span>
              <span className="v">
                <a href={`${links.github}/blob/main/agent/RULES.md`} target="_blank" rel="noreferrer">
                  Published in the repo
                </a>
              </span>
            </div>
            <div className="kv">
              <span className="k">Build log</span>
              <span className="v">
                <a href={`${links.github}/blob/main/BUILDLOG.md`} target="_blank" rel="noreferrer">
                  Day by day, in public
                </a>
              </span>
            </div>
            <div className="kv">
              <span className="k">Price data</span>
              <span className="v">
                <a href={links.api} target="_blank" rel="noreferrer">
                  Coinbase Tokenized Stocks API
                </a>
              </span>
            </div>
            <p className="empty">
              The agent&apos;s own activity lives on a testnet. The tokenized
              stocks themselves are never bought or sold by StockSage.
            </p>
          </div>
        </div>
      </section>

      {/* ---------- footer ---------- */}
      <footer>
        <p>
          <strong style={{ color: "var(--muted)" }}>
            Simulated portfolio. Not financial advice.
          </strong>{" "}
          StockSage is a research and education project. Nothing on this page is
          a recommendation to buy or sell anything, and the portfolio shown is
          simulated with virtual funds — no real money and no real securities
          are involved.
        </p>
        <p>
          Prices are NAV reference values from the Coinbase Tokenized Stocks API
          (Base mainnet, chain 8453), shown with their last-update timestamps.
          Page generated {generated} from the agent&apos;s public records.
        </p>
      </footer>
    </div>
  );
}
