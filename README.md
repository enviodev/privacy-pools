# Privacy Pools Indexer

An open-source [Envio HyperIndex](https://docs.envio.dev) v3 indexer for the
[Privacy Pools](https://privacypools.com) protocol, plus a Python analytics
package for running BI queries against the ClickHouse sink.

Companion to the [Privacy in Public](https://docs.envio.dev/privacy-in-public-case-study)
case study.

## What it indexes

A single multichain indexer covering every live Privacy Pools deployment:

| Chain | Chain ID | Pools |
|---|---|---|
| Ethereum | 1 | 14 (ETH, USDC, USDT, DAI, USDS, sUSDS, fxUSD, frxUSD, USDe, USD1, wstETH, wOETH, WBTC, BOLD) |
| Optimism | 10 | 2 (ETH, USDC) |
| BNB Smart Chain | 56 | 2 (BNB, USDT) |
| Arbitrum | 42161 | 3 (ETH, yUSND, USDC) |

Every event is captured: `Deposited`, `Withdrawn`, `Ragequit`, `LeafInserted`,
`PoolDied`, plus the Entrypoint's lifecycle and ASP-root events.

A thin Uniswap V4 price feed runs on BNB Smart Chain only, near chain head, to
provide current USD prices for ETH, BTC, BNB and the major stables. No
historical V4 backfill, just a real-time price layer.

Multichain sync to head: ~30 seconds via [HyperSync](https://docs.envio.dev/docs/HyperSync/overview).

## Layout

```
config.yaml                Multichain config (all 4 chains, all 21 pools)
schema.graphql             9 entity types: Pool, Deposit, Withdrawal,
                           Ragequit, MerkleLeaf, AssociationSetRoot,
                           Account, FeeWithdrawal, plus TokenPrice /
                           LatestPrice from the V4 feed
src/
  EventHandlers.ts         All onEvent handlers
  assets.ts                Per-chain asset metadata (symbol, decimals)
  v4Pricing.ts             BSC pricing whitelist + sqrtPriceX96 derivation
  v4PoolMeta.ts            Hardcoded V4 pool metadata (snapshot)
  v4PoolIds.ts             Hardcoded V4 pool ID filter for Swap events

analytics/
  pyproject.toml           uv-managed Python deps
  CLAUDE.md                Schema reference + query index for agents
  README.md                Analytics package overview
  lib/                     ClickHouse connector, casts/filters, charts
  queries/                 Saved parameterised .sql queries by domain
  scripts/
    generate_bi_report.py  Runs queries, charts, writes the BI report
    render_pdf.py          Markdown to PDF
    generate_blog_header.py  Reproduces the blog headline image
```

## Running locally

Prerequisites: Node 22+, pnpm 8+, Docker, and [`uv`](https://github.com/astral-sh/uv).

```bash
# Indexer
cp .env.example .env
# Add your ENVIO_API_TOKEN (free at https://envio.dev/app/api-tokens)
pnpm install
pnpm envio start            # starts Postgres + ClickHouse + Hasura locally,
                            # then runs the indexer to chain head

# Analytics + BI report (in another shell)
cd analytics
cp .env.example .env
uv sync
uv run python scripts/generate_bi_report.py
uv run python scripts/render_pdf.py output/bi_report_$(date +%F).md
```

`http://localhost:8080` opens the Hasura GraphQL playground (admin secret
`testing`). `http://localhost:8123` is the ClickHouse HTTP endpoint.

## Saved queries

Every metric in the case-study post is one `.sql` file under
`analytics/queries/`. See `analytics/queries/README.md` for the full index.
Workflow: read the `.sql` file, substitute `{{param}}` defaults, run via
`lib/db.py` (which sets the `envio_sink` database context).

Domains:

- `health/` operational status (indexer freshness, pool overview, TVL)
- `anonymity/` anonymity-set growth and current size
- `risk/` linkability heuristic, decoy-withdrawal candidates, ragequit
  rate, depositor concentration, round-amount share
- `asp/` Association Set Provider root cadence
- `relayers/` relayer market share, relayed-vs-self-submitted split
- `fees/` Entrypoint fee withdrawals
- `activity/` daily / hourly heatmap / size distribution / dwell time
- `pricing/` BSC V4 latest prices, USD-valued TVL

## Extending the analysis

Every entity carries `chainId` and `blockNumber`, and IDs are chain-scoped
(`{chainId}_{address}` for pools, `{chainId}_{txHash}-{logIndex}` for events).
Adding a new heuristic is a `.sql` file under `analytics/queries/`, not a
re-index.

The schema is documented end-to-end in `analytics/CLAUDE.md`, including the
BigInt/timestamp string-cast convention used by the ClickHouse sink.

## License

MIT. See [LICENSE](./LICENSE).
