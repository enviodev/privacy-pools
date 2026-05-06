-- Description: Distribution of "dwell time" buckets across all chains.

WITH pairs AS (
    SELECT
        d.chainId,
        d.poolAddress,
        d.assetSymbol,
        toUInt64(w.timestamp) - toUInt64(d.timestamp) AS gap_seconds
    FROM "Deposit" d
    JOIN "Withdrawal" w
      ON  w.pool                = d.pool
     AND  w.withdrawnValue      = d.value
     AND  toUInt64(w.timestamp) >  toUInt64(d.timestamp)
)
SELECT
    chainId                                                    AS chain_id,
    assetSymbol                                                AS asset,
    if(gap_seconds < 600,           '<10m',
     if(gap_seconds < 3600,         '10m-1h',
     if(gap_seconds < 86400,        '1h-1d',
     if(gap_seconds < 7 * 86400,    '1d-1w',
     if(gap_seconds < 30 * 86400,   '1w-1mo',
                                    '>1mo')))))               AS bucket,
    count()                                                    AS pairs
FROM pairs
GROUP BY chainId, assetSymbol, bucket
ORDER BY chainId, assetSymbol, bucket
