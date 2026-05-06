-- Description: Per-token daily VWAP-style summary (mean priceUsd
-- weighted by swap count) from BSC V4 pricing.
-- Parameters:
--   {{days}} - look-back window (default: 60)

SELECT
    symbol                                                    AS symbol,
    toDate(toDateTime(toUInt64(timestamp)))                   AS day,
    avg(toFloat64(toString(priceUsd)))                        AS avg_price,
    min(toFloat64(toString(priceUsd)))                        AS min_price,
    max(toFloat64(toString(priceUsd)))                        AS max_price,
    count()                                                   AS observations
FROM "TokenPrice"
WHERE toDate(toDateTime(toUInt64(timestamp))) >= today() - {{days}}
GROUP BY symbol, day
ORDER BY symbol, day
