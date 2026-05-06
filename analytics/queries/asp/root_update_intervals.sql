-- Description: Per-chain distribution of intervals between consecutive
-- ASP root updates.

WITH ts AS (
    SELECT chainId, toUInt64(rootTimestamp) AS t
    FROM "AssociationSetRoot"
),
gaps AS (
    SELECT chainId,
           t - lagInFrame(t, 1, 0) OVER (PARTITION BY chainId ORDER BY t) AS gap_seconds
    FROM ts
)
SELECT
    chainId                                          AS chain_id,
    count()                                          AS update_count,
    floor(min(gap_seconds))                          AS min_gap_seconds,
    floor(quantile(0.5)(gap_seconds))                AS median_gap_seconds,
    floor(quantile(0.95)(gap_seconds))               AS p95_gap_seconds,
    floor(max(gap_seconds))                          AS max_gap_seconds
FROM gaps
WHERE gap_seconds > 0
GROUP BY chainId
ORDER BY chainId
