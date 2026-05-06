"""SQL fragment helpers for the Privacy Pools indexer ClickHouse sink.

The sink stores BigInts and BigInt-like timestamps as ``String`` to
preserve precision. These helpers hide that wart: cast every
``timestamp`` before comparing/truncating, and every ``value`` /
``totalDepositValue`` / ``feeAmount`` / etc. before arithmetic.
"""

from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Chain helpers
# ---------------------------------------------------------------------------

CHAIN_NAMES: dict[int, str] = {
    1: "Ethereum",
    10: "Optimism",
    56: "BSC",
    42161: "Arbitrum",
}


def chain_name_case(column: str = "chainId") -> str:
    """Return a SQL CASE expression mapping chainId -> human name."""
    whens = "\n        ".join(
        f"WHEN {cid} THEN '{name}'" for cid, name in CHAIN_NAMES.items()
    )
    return (
        f"CASE {column}\n        {whens}\n"
        f"        ELSE toString({column})\n    END"
    )


def chain_filter(chain_ids: int | list[int] | None) -> str:
    """AND clause restricting to one or more chainIds. Empty when None."""
    if chain_ids is None:
        return ""
    if isinstance(chain_ids, int):
        return f"AND chainId = {chain_ids}"
    ids = ",".join(str(c) for c in chain_ids)
    return f"AND chainId IN ({ids})"


# ---------------------------------------------------------------------------
# Timestamp helpers (schema stores seconds-since-epoch as String)
# ---------------------------------------------------------------------------


def ts_as_datetime(column: str = "timestamp") -> str:
    return f"toDateTime(toUInt64({column}))"


def ts_as_date(column: str = "timestamp") -> str:
    return f"toDate(toDateTime(toUInt64({column})))"


def recent_days(n: int, column: str = "timestamp") -> str:
    start = (date.today() - timedelta(days=n)).isoformat()
    return f"AND {ts_as_date(column)} >= toDate('{start}')"


def date_range(start: str, end: str, column: str = "timestamp") -> str:
    return (
        f"AND {ts_as_date(column)} >= toDate('{start}') "
        f"AND {ts_as_date(column)} <= toDate('{end}')"
    )


# ---------------------------------------------------------------------------
# BigInt helpers (raw token amounts are stored as String)
# ---------------------------------------------------------------------------


def amount_as_float(column: str) -> str:
    """Cast a BigInt-as-String column to Float64. Use only when the magnitudes
    are small enough to fit in a double (fine for token-units and up to ~1e15)."""
    return f"toFloat64OrZero({column})"


def amount_as_uint(column: str) -> str:
    return f"toUInt256OrZero({column})"


# ---------------------------------------------------------------------------
# Pool / asset metadata — pulled from the indexer's static map.
# Mirrors src/assets.ts. Keep in sync if new pools register on chain.
# ---------------------------------------------------------------------------

def pool_normalised_amount(amount_column: str, decimals_column: str = "assetDecimals") -> str:
    """Project a raw uint256-as-string value column as token-units (float).
    Multi-chain note: assetDecimals is on the Pool row; queries should join
    Pool to pull it rather than relying on a hardcoded address→decimals map."""
    return f"toFloat64OrZero({amount_column}) / pow(10, {decimals_column})"
