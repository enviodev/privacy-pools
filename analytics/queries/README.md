# Query index

All queries are parameterised with `{{name}}` placeholders. Defaults are
in each file's header comment. Read `../CLAUDE.md` for the schema and
workflow.

The indexer is multi-chain (Ethereum, Optimism, BSC, Arbitrum). Most
queries project `chain_id` so you can filter or group cleanly.

## health/

| File | What it answers |
|---|---|
| `indexer_freshness.sql` | Per-chain latest block + wall-clock lag |
| `pools_overview.sql` | Every pool, every chain, with headline counters |
| `tvl_by_pool.sql` | Token-units balance per pool (deposits − withdrawals − ragequits) |

## anonymity/

| File | What it answers |
|---|---|
| `current_set_size.sql` | Anonymity set size per pool, all chains |
| `set_growth_daily.sql` | ★ Daily leaves-at-day-end per pool over time |

## risk/

| File | What it answers |
|---|---|
| `same_actor_pairs.sql` | ★ Same-amount, time-windowed deposit→withdrawal pairs |
| `same_actor_summary.sql` | Per-pool: how many withdrawals are linkable, median gap |
| `mirror_deposits.sql` | ★ Third-party deposits mirroring a recent withdrawal |
| `ragequit_rate.sql` | Per-pool ragequit rate (ASP-curation health) |
| `depositor_concentration.sql` | Top depositors per pool with share of TVL |
| `concentration_summary.sql` | ★ Top-1 / top-5 / top-10 share + HHI per pool |
| `round_amount_share.sql` | Round-amount deposit share (privacy-weakening) |

## asp/

| File | What it answers |
|---|---|
| `root_update_cadence.sql` | Recent ASP root publications, per chain |
| `root_update_intervals.sql` | Distribution of intervals between root updates |

## relayers/

| File | What it answers |
|---|---|
| `relayer_share.sql` | ★ Per-chain relayer market share |
| `relay_vs_direct.sql` | Per-pool relayed vs self-submitted withdrawal share |

## fees/

| File | What it answers |
|---|---|
| `fee_withdrawals.sql` | When and how much the operator drained from accumulated fees |

## activity/

| File | What it answers |
|---|---|
| `daily_activity.sql` | Per-chain daily deposits/withdrawals/ragequits |
| `hourly_heatmap.sql` | Day-of-week × hour-of-day heatmap (all chains) |
| `deposit_size_distribution.sql` | Powers-of-10 amount buckets per pool |
| `time_to_withdraw.sql` | Bucketed dwell time between deposit and matched withdrawal |

## pricing/ — Uniswap V4 (BSC, head-only)

| File | What it answers |
|---|---|
| `latest_prices.sql` | ★ Most recent USD price per token from BSC V4 |
| `price_history_daily.sql` | Daily min/avg/max price per token (rolling window only) |
| `tvl_by_pool_usd.sql` | ★ USD-valued TVL per pool (BSC V4 prices + stable assumption) |

★ = headline queries surfaced in the management BI report.
