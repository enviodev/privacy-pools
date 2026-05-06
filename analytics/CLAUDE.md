# privacy-pools-analytics — agent instructions

You are the analytics engine for the Privacy Pools indexer. When the
user asks a question about pools, deposits, withdrawals, ragequits,
anonymity, relayers, fees, ASP roots, or token prices, query
ClickHouse, summarise the answer, and chart it if a chart helps.

## Setup

```bash
uv sync
cp .env.example .env   # defaults already target the local ClickHouse
```

ClickHouse must be running. With `storage.clickhouse: true` in
`../config.yaml`, `envio dev` auto-launches a local container. To start
the indexer from the repo root:

```bash
ENVIO_TUI=false pnpm envio start
```

## Generate the management report

```bash
uv run python scripts/generate_bi_report.py
uv run python scripts/render_pdf.py output/bi_report_<date>.md
```

## ClickHouse connection

Use `lib/db.py` for every query — it sets the `envio_sink` database
context, so queries can reference `"Pool"` etc. without a schema prefix.

```python
from lib.db import query, query_df
rows = query('SELECT count() FROM "Deposit"')
df = query_df('SELECT chainId, count() FROM "MerkleLeaf" GROUP BY chainId')
```

- Connection is **READ-ONLY**. Never write.
- All queries automatically receive `SETTINGS max_execution_time = 30`.
- Tables are written by the HyperIndex V3 ClickHouse sink.

## Chains indexed

The indexer is multi-chain. **Every entity has a `chainId` column.**

| chainId | name | role |
|---|---|---|
| 1 | Ethereum | 14 pools — original deployment, most activity |
| 10 | Optimism | 2 pools (ETH, USDC) |
| 56 | BSC | 2 pools (BNB, USDT) + Uniswap V4 PoolManager (pricing) |
| 42161 | Arbitrum | 3 pools (ETH, yUSND, USDC) |

Helper in `lib/filters.py`: `chain_name_case()` projects a friendly
name; `chain_filter(ids)` builds an `AND chainId IN (…)` clause.

## Critical schema quirk: BigInts and timestamps are strings

The sink preserves precision by storing `BigInt` columns and
unix-second timestamps as `String`. Cast before arithmetic.

| Column | Stored as | Real type |
|---|---|---|
| `Deposit.value` / `Deposit.commitment` / `Deposit.label` | String | uint256 |
| `Withdrawal.withdrawnValue` / `spentNullifier` / `newCommitment` | String | uint256 |
| `Pool.totalDepositValue` / `totalWithdrawalValue` / `totalRagequitValue` | String | uint256 |
| `Pool.scope` / `currentRoot` / `minimumDepositAmount` | String | uint256 |
| `MerkleLeaf.leaf` / `root` | String | uint256 |
| `AssociationSetRoot.root` / `rootTimestamp` / `blockTimestamp` | String | uint256 |
| `*.timestamp` / `Pool.registeredAt` / `Pool.lastUpdatedAt` | String | unix seconds |
| `*.blockNumber` / `Pool.assetDecimals` / `Pool.totalDeposits` | Int32 | int |
| `Pool.windDown` / `Pool.poolDied` | Bool | bool |
| `TokenPrice.priceUsd` / `LatestPrice.priceUsd` | String | BigDecimal USD |

Helpers in `lib/filters.py`:

```python
from lib.filters import (
    ts_as_datetime, ts_as_date, recent_days, date_range,
    amount_as_float, pool_normalised_amount,
    chain_name_case, chain_filter, CHAIN_NAMES,
)
```

Inline SQL equivalents:

```sql
toDateTime(toUInt64(timestamp))                -- String → DateTime
toDate(toDateTime(toUInt64(timestamp)))        -- String → Date
toFloat64OrZero(value)                         -- BigInt → Float64
toFloat64(toString(priceUsd))                  -- BigDecimal → Float64
toFloat64OrZero(d.value) / pow(10, p.assetDecimals) -- normalise to token-units
```

## Identity / id conventions

Multi-chain forced new id schemes — IDs collide otherwise (the L2 ETH
pools all share address `0x4626…918ff`).

| Entity | id format |
|---|---|
| Pool | `{chainId}_{lowercaseAddress}` |
| Deposit / Withdrawal / Ragequit / FeeWithdrawal / AssociationSetRoot | `{chainId}_{txHash}-{logIndex}` |
| MerkleLeaf | `{chainId}_{lowercaseAddress}-{leafIndex}` |
| Account | lowercase address (cross-chain rollup; same person, same id) |
| TokenPrice | `{chainId}_{txHash}-{logIndex}_{token}` |
| LatestPrice | `{chainId}_{token}` (upserted on every TokenPrice write) |
| V4Pool | `{chainId}_{poolId}` (poolId is the bytes32 hex) |

For joins, prefer `Deposit.pool = Pool.id` (both chainId-scoped).
`Deposit.poolAddress` is the convenience column with just the address.

## Schema reference

**`Pool`** — one row per registered pool.
| Column | Notes |
|---|---|
| id | `{chainId}_{address}` |
| chainId | indexed |
| address | lowercase pool address |
| scope | uint256 — on-chain scope |
| asset / assetSymbol / assetDecimals | underlying token |
| minimumDepositAmount / vettingFeeBPS / maxRelayFeeBPS | uint256 |
| registeredAt / registeredBlock | block when PoolRegistered fired |
| lastUpdatedAt / lastUpdatedBlock | most recent event touching the pool |
| windDown / poolDied | lifecycle |
| totalDeposits / totalWithdrawals / totalRagequits | running counts |
| totalDepositValue / totalWithdrawalValue / totalRagequitValue | uint256 |
| currentLeafCount / currentRoot | tree state |

**`Deposit`** — one row per `PrivacyPool.Deposited`. Patched in-place when
the matching `Entrypoint.Deposited` lands in the same tx.
`pool` = chainId-scoped Pool.id, `poolAddress` = just the lowercase address.
`vettingFee` is structurally always 0 because Entrypoint.Deposited emits
post-fee values — see fees section in CLAUDE for the workaround.

**`Withdrawal`** — one row per `PrivacyPool.Withdrawn`. Patched with
`{relayer, recipient, feeAmount}` if a matching `WithdrawalRelayed`
fires in the same tx (then `isRelayed = true`).

**`Ragequit`** — escape-hatch withdrawals.
**`MerkleLeaf`** — one row per `LeafInserted`. id `{chainId}_{address}-{index}`.
**`AssociationSetRoot`** — one row per `RootUpdated`.
**`Account`** — per-address rollup (cross-chain): firstSeen, firstSeenBlock,
firstSeenChain, lastSeen, lastSeenBlock, depositCount, withdrawalCount,
ragequitCount.
**`FeeWithdrawal`** — one row per `FeesWithdrawn`. The authoritative fee cashflow.

### Pricing entities (BSC Uniswap V4)

**`V4Pool`** — every BSC V4 pool that has at least one whitelisted token
on each side AND at least one stable side. Records the PoolKey
(currency0, currency1, fee, tickSpacing, hooks) plus rolling swap stats.

**`TokenPrice`** — one row per relevant V4 swap, recording the derived
USD price for the non-stable side (USD per token, BigDecimal).

**`LatestPrice`** — upserted on every `TokenPrice` write; one row per
(chain, token) with the most recent priceUsd.

Pricing notes:

- BSC V4 pools sourced for: WBNB, WETH, BTCB, plus stable/stable for
  peg validation. Stables (USDC, USDT, DAI on BSC) are anchored at $1.
- Ethereum-only assets (USDS, sUSDS, fxUSD, BOLD, frxUSD, USDe, USD1,
  yUSND, wOETH, wstETH) have no BSC V4 liquidity. Treat known stables
  as $1, derive ETH-derivatives (wstETH/wOETH) from ETH price if needed.
- The `pricing/tvl_by_pool_usd.sql` query already encodes this fallback.

## Saved queries

See `queries/README.md` for the index. Parameters use `{{name}}`.

### Question → query map

| User question | Query |
|---|---|
| Per-chain freshness? | `queries/health/indexer_freshness.sql` |
| Pools across all chains? | `queries/health/pools_overview.sql` |
| Token-units TVL per pool? | `queries/health/tvl_by_pool.sql` |
| **USD-valued TVL?** | `queries/pricing/tvl_by_pool_usd.sql` |
| Anonymity-set growth? | `queries/anonymity/set_growth_daily.sql` |
| Linkability heuristic? | `queries/risk/same_actor_summary.sql` |
| Mirror-deposit pattern? | `queries/risk/mirror_deposits.sql` |
| Ragequit hot spots? | `queries/risk/ragequit_rate.sql` |
| Depositor concentration / HHI? | `queries/risk/concentration_summary.sql` |
| Relayer market share? | `queries/relayers/relayer_share.sql` |
| Self-relay vs relay split? | `queries/relayers/relay_vs_direct.sql` |
| Fee withdrawals? | `queries/fees/fee_withdrawals.sql` |
| Daily activity? | `queries/activity/daily_activity.sql` |
| Latest USD prices? | `queries/pricing/latest_prices.sql` |
| V4 pricing pools discovered? | `queries/pricing/v4_pools.sql` |

## Workflow rules

1. **Always show the SQL you ran.** Reproducibility matters.
2. **Cast BigInt strings** before arithmetic — `toFloat64OrZero(value)`
   for token-units, `toUInt64(timestamp)` for time math.
3. **Quote CamelCase table names** (`"Pool"`, `"Deposit"`, etc.).
4. **Project chainId** on every per-pool result; default behaviour is
   "all chains aggregated", but caller can filter on `chain_id`.
5. **Use `Pool.id` for joins**, not `Pool.address`. The id is
   chain-scoped; address is not.
6. **Normalise to token units** by joining `Pool` for `assetDecimals`.
7. **For USD figures, prefer `pricing/tvl_by_pool_usd.sql`** which
   already encodes the stable-anchor + V4 fallback rules.
8. **No external pricing.** Don't invent USD prices — quote what
   `LatestPrice` gives, fall back to $1 for known stables, mark
   unpriced for everything else.
9. **Default look-back:** 30 days for trend questions, 60–120 days for
   heatmaps and patterns.
10. **Mention the data freshness** (latest block + per-chain lag) when
    reporting numbers.

## Privacy-relevant interpretation cheat-sheet

- **Linkable share** (`risk/same_actor_summary.sql`) = withdrawals
  matching a same-amount deposit within 1m–2h. Rough upper bound on
  the fraction of withdrawals tied to a deposit by this heuristic.
- **HHI** (`risk/concentration_summary.sql`) — Herfindahl-Hirschman
  Index on depositor share, ×10000. >2500 ≈ "highly concentrated".
- **Ragequit rate** (`risk/ragequit_rate.sql`) — fraction of deposit
  value that left through the escape hatch. High rates suggest
  ASP-vetting churn rather than ordinary user behaviour.
- **Mirror-deposit count** (`risk/mirror_deposits.sql`) — third-party
  deposits matching a recent withdrawal within 30min. Either
  deliberate obfuscation or coincidence on a popular round amount.

## Caveats

- **Per-event start blocks**: USDC/USDT/BOLD on Ethereum, and the
  L2 pools on Optimism/BSC/Arbitrum, were registered after the
  Entrypoint. Their event tables are sparse for the early indexer
  history. Always check `Pool.registeredBlock` before commenting on
  time-series gaps.
- **`assetDecimals` is hard-coded** in `src/assets.ts` against a known
  list of pool addresses (per chain). New pools will show as
  `UNKNOWN`/decimals=18 until added.
- **No mainnet V4 pricing yet** — only BSC. ETH-mainnet exotic tokens
  (USDS, fxUSD, BOLD, …) ride on the stable-peg assumption. If any
  de-pegs, USD figures drift silently.
- **Vetting fee is structurally 0** in the `Deposit` table — the
  Entrypoint emits post-fee values, so the gross/net split isn't
  derivable from event data alone. Use `FeeWithdrawal` for fee cashflow.

## Known state (as of session start)

- Indexer: HyperIndex V3 (envio `3.0.0-rc.0`).
- Storage: dual Postgres + ClickHouse via `storage:` block.
- Chains: Ethereum (1) + Optimism (10) + BSC (56) + Arbitrum (42161).
- 21 PrivacyPool instances + Entrypoint per chain + UniswapV4PoolManager
  on BSC for pricing.
- DRPC API key present in `../.env` (for ad-hoc on-chain reads via
  effects API or external scripts).
