-- Description: Per-pool deposit-amount histogram (powers-of-10 buckets,
-- in token units, multi-chain).

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
    chainId                                                                      AS chain_id,
    assetSymbol                                                                  AS asset,
    poolAddress                                                                  AS pool_address,
    if(amount < 0.001, '<0.001',
      if(amount < 0.01,  '0.001-0.01',
      if(amount < 0.1,   '0.01-0.1',
      if(amount < 1,     '0.1-1',
      if(amount < 10,    '1-10',
      if(amount < 100,   '10-100',
      if(amount < 1000,  '100-1k',
      if(amount < 10000, '1k-10k',
                         '>10k'))))))))                                         AS bucket,
    count()                                                                      AS deposits
FROM normalised
GROUP BY chainId, poolAddress, assetSymbol, bucket
ORDER BY chainId, poolAddress, bucket
