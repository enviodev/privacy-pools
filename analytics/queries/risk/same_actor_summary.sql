-- Description: Aggregate the same-actor heuristic per (chain, pool).
-- Parameters:
--   {{min_gap}} - minimum gap seconds (default: 60)
--   {{max_gap}} - maximum gap seconds (default: 7200)

WITH pairs AS (
    SELECT
        d.pool       AS pool,
        toUInt64(w.timestamp) - toUInt64(d.timestamp) AS gap_seconds,
        w.id         AS withdrawal_id
    FROM "Deposit" d
    JOIN "Withdrawal" w
      ON  w.pool                = d.pool
     AND  w.withdrawnValue      = d.value
     AND  toUInt64(w.timestamp) >  toUInt64(d.timestamp)
     AND (toUInt64(w.timestamp) -  toUInt64(d.timestamp)) BETWEEN {{min_gap}} AND {{max_gap}}
),
withdrawals AS (
    SELECT pool, count() AS total_withdrawals FROM "Withdrawal" GROUP BY pool
)
SELECT
    p.chainId                                                           AS chain_id,
    p.assetSymbol                                                       AS asset,
    p.address                                                           AS pool_address,
    coalesce(pr.candidate_pairs, 0)                                     AS candidate_pairs,
    coalesce(pr.linkable_withdrawals, 0)                                AS linkable_withdrawals,
    w.total_withdrawals                                                 AS total_withdrawals,
    if(w.total_withdrawals > 0,
       coalesce(pr.linkable_withdrawals, 0) / w.total_withdrawals,
       0)                                                               AS linkable_pct,
    pr.median_gap_seconds                                               AS median_gap_seconds
FROM "Pool" p
LEFT JOIN withdrawals w ON w.pool = p.id
LEFT JOIN (
    SELECT pool,
           count()                            AS candidate_pairs,
           uniqExact(withdrawal_id)           AS linkable_withdrawals,
           floor(quantile(0.5)(gap_seconds))  AS median_gap_seconds
    FROM pairs
    GROUP BY pool
) pr ON pr.pool = p.id
WHERE w.total_withdrawals > 0
ORDER BY linkable_pct DESC
