-- Description: Daily counts of deposits, withdrawals, and ragequits.
-- Optionally per-chain (filter on the projected chain_id).
-- Parameters:
--   {{days}} - look-back window (default: 60)

WITH ev AS (
    SELECT chainId, 'deposit'   AS kind, timestamp FROM "Deposit"
    UNION ALL
    SELECT chainId, 'withdraw'  AS kind, timestamp FROM "Withdrawal"
    UNION ALL
    SELECT chainId, 'ragequit'  AS kind, timestamp FROM "Ragequit"
)
SELECT
    chainId                                           AS chain_id,
    toDate(toDateTime(toUInt64(timestamp)))           AS day,
    countIf(kind = 'deposit')                         AS deposits,
    countIf(kind = 'withdraw')                        AS withdrawals,
    countIf(kind = 'ragequit')                        AS ragequits
FROM ev
WHERE toDate(toDateTime(toUInt64(timestamp))) >= today() - {{days}}
GROUP BY chainId, day
ORDER BY chainId, day
