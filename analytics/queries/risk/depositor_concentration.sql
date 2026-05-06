-- Description: Top depositors per pool (multi-chain) with their share of TVL.
-- Parameters:
--   {{top_n}} - depositors per pool to return (default: 10)

WITH per AS (
    SELECT depositor, pool, sum(toUInt256OrZero(value)) AS total_raw
    FROM "Deposit"
    GROUP BY depositor, pool
),
ranked AS (
    SELECT pool, depositor, total_raw,
           row_number() OVER (PARTITION BY pool ORDER BY total_raw DESC) AS rk,
           sum(total_raw) OVER (PARTITION BY pool)                       AS pool_total_raw
    FROM per
)
SELECT
    p.chainId                                                      AS chain_id,
    p.assetSymbol                                                  AS asset,
    p.address                                                      AS pool_address,
    r.depositor                                                    AS depositor,
    toFloat64(r.total_raw) / pow(10, p.assetDecimals)              AS amount,
    if(r.pool_total_raw > 0,
       toFloat64(r.total_raw) / toFloat64(r.pool_total_raw), 0)    AS share_of_pool,
    r.rk                                                           AS rank
FROM ranked r
JOIN "Pool" p ON p.id = r.pool
WHERE r.rk <= {{top_n}}
ORDER BY p.chainId, r.pool, r.rk
