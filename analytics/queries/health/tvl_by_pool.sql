-- Description: On-pool token-units balance per pool, derived as
-- (deposits − withdrawals − ragequits). USD valuation is now optional —
-- join LatestPrice to project priceUsd. Pair with stablecoin convention
-- of $1.00 for assets we know are pegged.

SELECT
    p.chainId                                                              AS chain_id,
    p.address                                                              AS pool_address,
    p.assetSymbol                                                          AS asset,
    p.assetDecimals                                                        AS decimals,
    toFloat64OrZero(p.totalDepositValue) / pow(10, p.assetDecimals)        AS deposited,
    toFloat64OrZero(p.totalWithdrawalValue) / pow(10, p.assetDecimals)     AS withdrawn,
    toFloat64OrZero(p.totalRagequitValue) / pow(10, p.assetDecimals)       AS ragequit,
    (toFloat64OrZero(p.totalDepositValue)
        - toFloat64OrZero(p.totalWithdrawalValue)
        - toFloat64OrZero(p.totalRagequitValue)) / pow(10, p.assetDecimals) AS tvl_native
FROM "Pool" p
WHERE p.windDown = false
ORDER BY tvl_native DESC
