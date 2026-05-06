# privacy-pools-analytics

Agent-native BI for the multi-chain Privacy Pools indexer (Ethereum +
Optimism + BSC + Arbitrum), with optional USD valuation sourced from
BSC Uniswap V4 swaps.

## Setup

```bash
uv sync
cp .env.example .env  # defaults point at the local ClickHouse container
```

Start the indexer from the repo root:

```bash
ENVIO_TUI=false pnpm envio start    # or: pnpm envio dev
```

## Generate the management BI report

```bash
uv run python scripts/generate_bi_report.py
uv run python scripts/render_pdf.py output/bi_report_<date>.md
```

Sections covered:

1. Per-chain at-a-glance + indexer freshness
2. Pool health (every pool, every chain)
3. Anonymity-set growth
4. Linkability heuristic (same-amount/time-window)
5. Depositor concentration (HHI)
6. Ragequit hot spots
7. Relayer market structure
8. Fees (FeesWithdrawn cashflow)
9. **USD-valued TVL** (BSC V4 prices + stable-peg assumption for unpriced tokens)
10. Activity patterns (daily, hourly heatmap)
11. Recommendations for management

## Ad-hoc questions

Open this folder in Claude Code and ask:

- "Top 5 pools by anonymity-set size on Optimism"
- "What's BNB priced at right now?"
- "Same-amount linkability rate for the BSC USDT pool"
- "Which relayer dominates Arbitrum?"

`CLAUDE.md` documents the schema, query map, and the privacy-quality
interpretation cheat-sheet so the agent can answer without further setup.

## Structure

```
lib/         # ClickHouse connector, casts/filters, charting helpers
queries/     # Saved parameterised .sql queries, grouped by domain
scripts/     # generate_bi_report.py + render_pdf.py
output/      # Generated charts + reports (gitignored)
CLAUDE.md    # Schema reference + query index for the agent
```

## Pricing layer (BSC Uniswap V4)

The indexer subscribes to a thin slice of BSC's V4 PoolManager:

- `Initialize` events filtered to pools where at least one currency is
  in our pricing whitelist (WBNB / WETH / BTCB / USDT / USDC / DAI on BSC).
- `Swap` events filtered to a pre-discovered list of ~70 pricing pool
  IDs (in `../src/v4PoolIds.ts`) — the only ones we actually need
  prices from.

Outputs:

- `TokenPrice` — one row per relevant V4 swap with derived USD price.
- `LatestPrice` — upserted per (chain, token) so a single row gives
  the most recent price.
- `V4Pool` — every discovered pricing pool with its config + rolling
  swap stats.

For tokens without BSC liquidity (USDS, sUSDS, fxUSD, BOLD, etc.)
the BI report falls back to a $1 stable assumption.
