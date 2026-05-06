-- Description: Per-(chain, pool) split of relayed vs self-submitted withdrawals.

SELECT
    chainId                                             AS chain_id,
    poolAddress                                         AS pool_address,
    assetSymbol                                         AS asset,
    countIf(isRelayed = true)                           AS relayed,
    countIf(isRelayed = false)                          AS self_relayed,
    count()                                             AS total,
    countIf(isRelayed = true) / count()                 AS relayed_share
FROM "Withdrawal"
GROUP BY chainId, poolAddress, assetSymbol
ORDER BY total DESC
