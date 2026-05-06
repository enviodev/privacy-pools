-- Description: Round-amount deposit share per pool (multi-chain).

WITH normalised AS (
    SELECT
        d.chainId,
        d.poolAddress,
        d.assetSymbol,
        toFloat64OrZero(d.value) / pow(10, p.assetDecimals) AS amount
    FROM "Deposit" d
    JOIN "Pool" p ON p.id = d.pool
)
SELECT
    chainId                                              AS chain_id,
    assetSymbol                                          AS asset,
    poolAddress                                          AS pool_address,
    count()                                              AS total_deposits,
    countIf(
        amount IN (0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000)
    )                                                    AS round_deposits,
    countIf(
        amount IN (0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000)
    ) / count()                                          AS round_share
FROM normalised
GROUP BY chainId, poolAddress, assetSymbol
ORDER BY round_share DESC
