"""Generate a management BI report for Privacy Pools from ClickHouse.

Multi-chain (Ethereum + Optimism + BSC + Arbitrum) plus optional USD
valuation via BSC Uniswap V4 prices. Runs the headline queries, renders
charts under ``output/``, writes ``output/bi_report_<YYYY-MM-DD>.md``.

Usage:
    uv run python scripts/generate_bi_report.py
    uv run python scripts/render_pdf.py output/bi_report_<date>.md
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from tabulate import tabulate

from lib.db import query, query_df
from lib.chart import bar_chart, heatmap, stacked_area, time_series
from lib.filters import CHAIN_NAMES


QUERY_DIR = ROOT / "queries"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)


def read_query(rel: str, **params) -> str:
    sql = (QUERY_DIR / rel).read_text()
    for k, v in params.items():
        sql = sql.replace("{{" + k + "}}", str(v))
    return sql


def chain_name(cid) -> str:
    try:
        return CHAIN_NAMES.get(int(cid), str(cid))
    except (TypeError, ValueError):
        return str(cid)


def fmt(n, dp: int = 0) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "—"
    if isinstance(n, (int, float)):
        if abs(n) >= 1e9:
            return f"{n/1e9:.2f}B"
        if abs(n) >= 1e6:
            return f"{n/1e6:.2f}M"
        if abs(n) >= 1e3:
            return f"{n/1e3:.2f}K"
        if dp == 0 and float(n).is_integer():
            return f"{int(n):,}"
        return f"{n:,.{dp}f}"
    return str(n)


def usd(n) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "—"
    if abs(n) >= 1e9:
        return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n/1e6:.2f}M"
    if abs(n) >= 1e3:
        return f"${n/1e3:.1f}K"
    return f"${n:,.2f}"


def md_table(df: pd.DataFrame, headers: list[str] | None = None) -> str:
    return tabulate(df.values.tolist(),
                    headers=headers or list(df.columns),
                    tablefmt="github",
                    floatfmt=",.4g")


def short(addr: str | None, n: int = 8) -> str:
    if not isinstance(addr, str):
        return "—"
    return addr[:n + 2] + "…" if len(addr) > n + 2 else addr


def label(row) -> str:
    """Compact pool label: chain:asset:0x1234abcd…"""
    return f"{chain_name(row['chain_id'])}:{row['asset']}:{short(row['pool_address'])}"


# ---------------------------------------------------------------------------


def section_header() -> tuple[str, dict]:
    fresh = query_df(read_query("health/indexer_freshness.sql"))
    pools = query_df(read_query("health/pools_overview.sql"))
    total_pools = len(pools)
    live_pools = int(((~pools["windDown"]) & (~pools["poolDied"])).sum())

    deposits = int(pools["totalDeposits"].sum())
    withdrawals = int(pools["totalWithdrawals"].sum())
    ragequits = int(pools["totalRagequits"].sum())
    leaves = int(pools["leaves"].sum())

    fresh = fresh.copy()
    fresh["chain"] = fresh["chain_id"].apply(chain_name)
    # `indexer_head` is where envio is at — this is the right "freshness"
    # number. `last_event_at` is just the most recent event that
    # produced a row, which can be days old even when fully synced.
    fresh_table = fresh[[
        "chain", "indexer_head", "events_processed",
        "last_event_block", "last_event_at",
    ]]

    chains_summary = pools.groupby("chain_id").agg(
        pools=("pool_address", "count"),
        deposits=("totalDeposits", "sum"),
        withdrawals=("totalWithdrawals", "sum"),
        ragequits=("totalRagequits", "sum"),
        leaves=("leaves", "sum"),
    ).reset_index()
    chains_summary["chain"] = chains_summary["chain_id"].apply(chain_name)
    chains_summary = chains_summary[["chain", "pools", "deposits", "withdrawals", "ragequits", "leaves"]]

    md = f"""# Privacy Pools — Management BI Report

*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.
Source: local ClickHouse sink populated by the HyperIndex v3 indexer
across Ethereum, Optimism, BSC, and Arbitrum.*

## At a glance

| Metric | Value |
|---|---|
| Pools registered | {fmt(total_pools)} ({fmt(live_pools)} live) |
| Lifetime deposits | {fmt(deposits)} |
| Lifetime withdrawals | {fmt(withdrawals)} |
| Lifetime ragequits | {fmt(ragequits)} |
| Total commitments in trees (anonymity-set leaves) | {fmt(leaves)} |

### Per-chain breakdown

{md_table(chains_summary)}

### Indexer state (per chain)

`indexer_head` is where envio has actually processed up to.
`last_event_block` / `last_event_at` is the most recent event that
produced a row — can be hours or days old even at chain head if the
protocol is quiet on that chain.

{md_table(fresh_table)}
"""
    ctx = {"pools": pools}
    return md, ctx


def section_pool_health(ctx: dict) -> str:
    df = ctx["pools"].copy()
    df["chain"] = df["chain_id"].apply(chain_name)
    df["pool"] = df["pool_address"].apply(short)
    df["registered_at"] = pd.to_datetime(df["registered_at"]).dt.strftime("%Y-%m-%d")
    table = df[[
        "chain", "asset", "pool", "registered_at",
        "totalDeposits", "total_deposit_value",
        "totalWithdrawals", "total_withdrawal_value",
        "totalRagequits", "leaves",
    ]].rename(columns={
        "totalDeposits": "deposits",
        "total_deposit_value": "deposit_amt",
        "totalWithdrawals": "withdrawals",
        "total_withdrawal_value": "withdraw_amt",
        "totalRagequits": "ragequits",
    })

    sizes = query_df(read_query("anonymity/current_set_size.sql")).copy()
    sizes["label"] = sizes.apply(label, axis=1)
    sizes = sizes.sort_values("leaves", ascending=True)
    bar_chart(
        sizes,
        x="label",
        y="leaves",
        title="Anonymity set size per pool (current leaf count)",
        filename="01_anonymity_set_size.png",
        ylabel="leaves",
        horizontal=True,
        figsize=(11, 8),
    )

    return f"""## 1. Pool health

Every pool registered through any Entrypoint, across all four chains.
Amounts are token-native (no USD conversion at the entity level — see
the pricing section for USD-valued TVL).

{md_table(table)}

![Anonymity set size per pool](01_anonymity_set_size.png)
"""


def section_anonymity() -> str:
    df = query_df(read_query("anonymity/set_growth_daily.sql", days=120))
    if df.empty:
        return ""
    df["day"] = pd.to_datetime(df["day"])
    df["chain"] = df["chain_id"].apply(chain_name)
    df["label"] = df["chain"] + ":" + df["pool_address"].apply(short)

    pivot = df.pivot_table(
        index="day", columns="label", values="leaves_at_day_end", aggfunc="max"
    ).ffill().fillna(0)

    keep = [c for c in pivot.columns if pivot[c].max() >= 5]
    if not keep:
        return ""
    pivot = pivot[keep].reset_index()

    stacked_area(
        pivot,
        x="day",
        y_cols=keep,
        title="Anonymity-set growth (leaves) per pool — last 120d",
        filename="02_anonymity_growth.png",
        ylabel="leaves",
        figsize=(13, 6),
    )

    return """## 2. Anonymity-set growth

Each commitment in the merkle tree is one leaf. Both deposits and the
ZK-replacement leaves emitted on withdrawal contribute. Larger sets
mean stronger plausible deniability for every depositor.

![Anonymity-set growth](02_anonymity_growth.png)
"""


def section_linkability() -> str:
    summary = query_df(read_query("risk/same_actor_summary.sql", min_gap=60, max_gap=7200))
    if summary.empty:
        return ""
    summary = summary.copy().sort_values("linkable_pct", ascending=False)
    summary["chain"] = summary["chain_id"].apply(chain_name)
    summary["label"] = summary["chain"] + ":" + summary["asset"]
    table = summary[[
        "chain", "asset", "candidate_pairs", "linkable_withdrawals",
        "total_withdrawals", "linkable_pct", "median_gap_seconds",
    ]].rename(columns={
        "candidate_pairs": "pairs",
        "linkable_withdrawals": "linkable_w",
        "total_withdrawals": "total_w",
        "linkable_pct": "linkable_share",
        "median_gap_seconds": "median_gap_s",
    })
    table["linkable_share"] = table["linkable_share"].apply(
        lambda x: f"{x*100:.1f}%" if x is not None else "—"
    )

    mirror = query_df(read_query("risk/mirror_deposits.sql", window=1800))
    mirror_n = len(mirror)
    mirror_uniq_recipients = mirror["withdrawal_recipient"].nunique() if not mirror.empty else 0

    bar_chart(
        summary,
        x="label",
        y="linkable_pct",
        title="Linkable withdrawal share — same-amount / 1m–2h heuristic",
        filename="03_linkable_share.png",
        ylabel="share of withdrawals",
        horizontal=False,
        figsize=(13, 5),
    )

    return f"""## 3. Linkability — the same-amount / time-window heuristic

For every (deposit, withdrawal) pair in the same pool with the same
on-chain value and a time gap of 60s–2h, the withdrawal is treated as
*linkable*. Headline privacy-quality metric.

{md_table(table)}

![Linkable withdrawal share by pool](03_linkable_share.png)

**Mirror-deposit pattern.** Deposits matching a recent withdrawal in
pool/value within 30 minutes from a different address. Found
**{fmt(mirror_n)}** mirror-pattern deposits across **{fmt(mirror_uniq_recipients)}**
distinct withdrawal recipients in the dataset.
"""


def section_concentration() -> str:
    df = query_df(read_query("risk/concentration_summary.sql"))
    if df.empty:
        return ""
    df = df.copy()
    df["chain"] = df["chain_id"].apply(chain_name)
    df["pool"] = df["pool_address"].apply(short)
    for col in ("top1_share", "top5_share", "top10_share"):
        df[col] = df[col].apply(lambda x: f"{x*100:.1f}%")
    table = df[[
        "chain", "asset", "pool", "unique_depositors",
        "top1_share", "top5_share", "top10_share", "hhi",
    ]].rename(columns={"unique_depositors": "depositors"})

    return f"""## 4. Depositor concentration

HHI is the Herfindahl-Hirschman Index on depositor-value share (×10000):
>2500 is "highly concentrated" by the US antitrust convention, and
roughly the threshold where the dominant depositor's identity leaks
through the anonymity set.

{md_table(table)}
"""


def section_ragequits() -> str:
    df = query_df(read_query("risk/ragequit_rate.sql"))
    if df.empty:
        return ""
    df = df.copy().sort_values("ragequit_value_rate", ascending=False)
    df["chain"] = df["chain_id"].apply(chain_name)
    df["pool"] = df["pool_address"].apply(short)
    df["count_rate"] = df["ragequit_count_rate"].apply(lambda x: f"{x*100:.1f}%")
    df["value_rate"] = df["ragequit_value_rate"].apply(lambda x: f"{x*100:.1f}%")

    table = df[[
        "chain", "asset", "pool", "totalDeposits", "totalRagequits",
        "count_rate", "value_rate",
    ]].rename(columns={"totalDeposits": "deposits", "totalRagequits": "ragequits"})

    chart_df = df[df["totalDeposits"] > 0].copy()
    chart_df["label"] = chart_df["chain"] + ":" + chart_df["asset"]
    chart_df["count_rate_num"] = chart_df["ragequit_count_rate"]
    bar_chart(
        chart_df.sort_values("count_rate_num", ascending=False),
        x="label",
        y="count_rate_num",
        title="Ragequit count rate per pool",
        filename="04_ragequit_rate.png",
        ylabel="rate",
        horizontal=False,
        figsize=(13, 5),
    )

    return f"""## 5. Ragequit rate — ASP-curation health

Ragequit is the escape hatch. Elevated ragequit rates indicate the ASP
is rejecting commitments that already entered the pool — either a
post-hoc vetting decision or a stale-set issue.

{md_table(table)}

![Ragequit count rate by pool](04_ragequit_rate.png)
"""


def section_relayers() -> str:
    rs = query_df(read_query("relayers/relayer_share.sql"))
    rd = query_df(read_query("relayers/relay_vs_direct.sql"))
    if rs.empty:
        return ""
    rs = rs.copy()
    rs["chain"] = rs["chain_id"].apply(chain_name)
    rs["relayer_short"] = rs["relayer"].apply(lambda r: short(r, 6))

    # Top per chain
    top_per_chain = (rs.sort_values(["chain_id", "relays"], ascending=[True, False])
                       .groupby("chain_id").head(5))
    rs_table = top_per_chain[[
        "chain", "relayer_short", "relays", "unique_recipients", "unique_pools",
    ]].rename(columns={"relayer_short": "relayer"})

    rd_total_relayed = int(rd["relayed"].sum()) if not rd.empty else 0
    rd_total_self = int(rd["self_relayed"].sum()) if not rd.empty else 0
    rd_total = rd_total_relayed + rd_total_self
    relay_pct = rd_total_relayed / rd_total * 100 if rd_total else 0

    return f"""## 6. Relayer market structure

Self-relayed withdrawals (recipient submits their own tx) link the
recipient to the gas-payer, weakening privacy. Concentrated relayer
markets create privacy chokepoints.

**Relayed share of withdrawals (all chains):** {relay_pct:.1f}% ({fmt(rd_total_relayed)} of {fmt(rd_total)}).

Top 5 relayers per chain:

{md_table(rs_table)}
"""


def section_fees() -> str:
    fw = query_df(read_query("fees/fee_withdrawals.sql"))
    if fw.empty:
        return """## 7. Fees

*No fee withdrawals recorded yet.*
"""
    fw = fw.copy()
    fw["chain"] = fw["chain_id"].apply(chain_name)

    by_chain_asset = fw.groupby(["chain", "asset"])["amount"].agg(["count", "sum"]).reset_index()
    by_chain_asset = by_chain_asset.rename(columns={"count": "withdrawals", "sum": "total_amount"})
    by_chain_asset = by_chain_asset.sort_values("total_amount", ascending=False)

    fw_recent = fw.head(8).copy()
    fw_recent["withdrew_at"] = pd.to_datetime(fw_recent["withdrew_at"]).dt.strftime("%Y-%m-%d")
    fw_recent["recipient"] = fw_recent["recipient"].apply(lambda r: short(r, 8))
    recent_table = fw_recent[["chain", "asset", "withdrew_at", "amount", "recipient"]]

    return f"""## 7. Fees

The Entrypoint accrues vetting + relay fees and emits `FeesWithdrawn`
when the operator drains. Event-data alone can't reconstruct the
gross/net split (events emit post-fee values), but `FeeWithdrawal`
records the authoritative cashflow.

**Total claimed per (chain, asset):**

{md_table(by_chain_asset)}

**Most recent withdrawals:**

{md_table(recent_table)}
"""


def section_activity() -> str:
    daily = query_df(read_query("activity/daily_activity.sql", days=60))
    if daily.empty:
        return ""
    daily["day"] = pd.to_datetime(daily["day"])
    rolled = daily.groupby("day")[["deposits", "withdrawals", "ragequits"]].sum().reset_index()
    time_series(
        rolled,
        x="day",
        y=["deposits", "withdrawals", "ragequits"],
        title="Daily protocol activity (all chains, last 60 days)",
        filename="05_daily_activity.png",
        ylabel="events",
        figsize=(12, 5),
    )

    heat = query_df(read_query("activity/hourly_heatmap.sql", days=120))
    if not heat.empty:
        DAY_LABEL = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        heat["dow"] = heat["dow"].map(DAY_LABEL)
        heatmap(
            heat,
            x="hour",
            y="dow",
            value="events",
            title="Activity by day-of-week × hour-of-day (UTC, last 120d)",
            filename="06_hourly_heatmap.png",
            figsize=(13, 4.5),
        )

    return """## 8. Activity patterns

![Daily protocol activity](05_daily_activity.png)

![Activity heatmap](06_hourly_heatmap.png)
"""


def section_pricing_and_tvl() -> str:
    """USD valuation via BSC V4 (head-only) prices."""
    latest = query_df(read_query("pricing/latest_prices.sql"))
    tvl = query_df(read_query("pricing/tvl_by_pool_usd.sql"))

    if latest.empty and tvl.empty:
        return """## 9. USD valuation (BSC Uniswap V4)

*No V4 price observations yet — leave the indexer running for a moment
to pick up a swap on each pricing pool.*
"""

    latest_table = latest[["symbol", "price_usd", "ref", "block", "observed_at"]]

    tvl = tvl.copy()
    tvl["chain"] = tvl["chain_id"].apply(chain_name)
    tvl["pool"] = tvl["pool_address"].apply(short)
    total_usd = float(tvl["tvl_usd"].dropna().sum()) if "tvl_usd" in tvl else 0.0
    tvl_table = tvl[["chain", "asset", "pool", "tvl_native", "price_usd", "tvl_usd"]]

    return f"""## 9. USD valuation (BSC Uniswap V4 — head-only)

Token prices derived from BSC Uniswap V4 swaps with a stablecoin
reference (USDC/USDT/DAI on BSC pegged at $1). The indexer doesn't
backfill V4 history — it only tracks the latest few days, refreshing
prices on every relevant swap. For tokens without BSC liquidity
(USDS, sUSDS, fxUSD, BOLD, frxUSD, USDe, USD1, yUSND) we assume $1
if they're stablecoins and skip valuation otherwise.

**Current USD prices:**

{md_table(latest_table)}

**Estimated total USD TVL across all chains:** {usd(total_usd)}

**Per-pool USD TVL:**

{md_table(tvl_table)}
"""


def section_recommendations() -> str:
    summary_df = query_df(read_query("risk/same_actor_summary.sql", min_gap=60, max_gap=7200))
    rq_df = query_df(read_query("risk/ragequit_rate.sql"))

    high_link = []
    if not summary_df.empty:
        for _, r in summary_df.sort_values("linkable_pct", ascending=False).head(3).iterrows():
            if r["linkable_pct"] and r["linkable_pct"] > 0.1:
                high_link.append((chain_name(r["chain_id"]), r["asset"], r["linkable_pct"]))

    high_rq = []
    if not rq_df.empty:
        for _, r in rq_df.sort_values("ragequit_value_rate", ascending=False).head(3).iterrows():
            if r["ragequit_value_rate"] and r["ragequit_value_rate"] > 0.1:
                high_rq.append((chain_name(r["chain_id"]), r["asset"], r["ragequit_value_rate"]))

    rec_lines = []
    if high_link:
        items = ", ".join(f"**{c}:{a}** ({p*100:.0f}%)" for c, a, p in high_link)
        rec_lines.append(
            f"- **Linkability hot spots:** {items}. Push relay-only withdrawal "
            "default for these assets — self-relayed withdrawals dominate the "
            "same-actor signal."
        )
    if high_rq:
        items = ", ".join(f"**{c}:{a}** ({p*100:.0f}%)" for c, a, p in high_rq)
        rec_lines.append(
            f"- **ASP exclusion churn:** {items} are seeing material value exit "
            "via ragequit. Audit ASP rejection logic and ragequit UX."
        )
    rec_lines.append(
        "- **Anonymity floor.** Pools below ~50 leaves provide weak deniability. "
        "Consider merging or sunsetting the long tail, or running a deposit "
        "incentive on the small chains/assets to reach a usable ~500-leaf floor."
    )
    rec_lines.append(
        "- **Round-amount nudge.** Round denominations (0.1, 1, 10) shrink the "
        "effective set against the same-amount heuristic. UI jitter "
        "(0.97-1.03) materially improves user privacy."
    )
    rec_lines.append(
        "- **Relayer concentration.** Track relayer share weekly per chain. "
        "Any single relayer above ~40% of flow becomes a privacy chokepoint."
    )
    rec_lines.append(
        "- **Cross-chain pricing gaps.** Several Ethereum-only assets (USDS, "
        "fxUSD, BOLD, etc.) are only priced via stable-peg assumption. If "
        "any of those de-peg, USD TVL figures drift silently. Consider "
        "extending the pricing layer with mainnet V4 for those tokens."
    )

    return "## 10. Recommendations for management\n\n" + "\n".join(rec_lines) + "\n"


def main() -> None:
    sections = []
    md, ctx = section_header()
    sections.append(md)
    sections.append(section_pool_health(ctx))
    sections.append(section_anonymity())
    sections.append(section_linkability())
    sections.append(section_concentration())
    sections.append(section_ragequits())
    sections.append(section_relayers())
    sections.append(section_fees())
    sections.append(section_activity())
    sections.append(section_pricing_and_tvl())
    sections.append(section_recommendations())

    report = "\n\n".join(s for s in sections if s)
    out_path = OUT_DIR / f"bi_report_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    out_path.write_text(report)
    print(f"wrote: {out_path}")
    print("charts in:", OUT_DIR)
    print("\nrender to PDF with:")
    print(f"  uv run python scripts/render_pdf.py {out_path}")


if __name__ == "__main__":
    main()
