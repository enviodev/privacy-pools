-- Description: Per-(chain, pool) concentration KPIs — top-1, top-5,
-- top-10 share + Herfindahl-Hirschman Index on depositor-value.

WITH per AS (
    SELECT depositor, pool, sum(toUInt256OrZero(value)) AS total_raw
    FROM "Deposit"
    GROUP BY depositor, pool
),
shared AS (
    SELECT pool, depositor, total_raw,
           sum(total_raw) OVER (PARTITION BY pool) AS pool_total
    FROM per
),
shares AS (
    SELECT
        pool,
        depositor,
        if(pool_total > 0, toFloat64(total_raw) / toFloat64(pool_total), 0) AS share,
        row_number() OVER (PARTITION BY pool ORDER BY total_raw DESC)        AS rk
    FROM shared
)
SELECT
    p.chainId                                                                    AS chain_id,
    p.assetSymbol                                                                AS asset,
    p.address                                                                    AS pool_address,
    uniqExact(s.depositor)                                                       AS unique_depositors,
    sumIf(s.share, s.rk = 1)                                                     AS top1_share,
    sumIf(s.share, s.rk <= 5)                                                    AS top5_share,
    sumIf(s.share, s.rk <= 10)                                                   AS top10_share,
    floor(sum(s.share * s.share * 10000))                                        AS hhi
FROM shares s
JOIN "Pool" p ON p.id = s.pool
GROUP BY p.chainId, p.address, p.assetSymbol
ORDER BY hhi DESC
