-- Description: Deposits + withdrawals by day-of-week × hour-of-day (UTC).
-- All chains aggregated. Filter via WHERE chainId = X if needed.
-- Parameters:
--   {{days}} - look-back window (default: 90)

SELECT
    toDayOfWeek(toDateTime(toUInt64(timestamp)))     AS dow,
    toHour(toDateTime(toUInt64(timestamp)))          AS hour,
    count()                                          AS events
FROM (
    SELECT timestamp FROM "Deposit"
    UNION ALL
    SELECT timestamp FROM "Withdrawal"
)
WHERE toDate(toDateTime(toUInt64(timestamp))) >= today() - {{days}}
GROUP BY dow, hour
ORDER BY dow, hour
