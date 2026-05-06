-- Description: Anonymity-set size per (chain, pool) per day.
-- Parameters:
--   {{days}} - look-back window (default: 90)

SELECT
    chainId                                           AS chain_id,
    poolAddress                                       AS pool_address,
    toDate(toDateTime(toUInt64(timestamp)))           AS day,
    max(index) + 1                                    AS leaves_at_day_end,
    count()                                           AS leaves_added_today
FROM "MerkleLeaf"
WHERE toDate(toDateTime(toUInt64(timestamp))) >= today() - {{days}}
GROUP BY chainId, poolAddress, day
ORDER BY chainId, poolAddress, day
