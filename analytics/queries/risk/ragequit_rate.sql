-- Description: Per-pool ragequit rate, multi-chain.

SELECT
    chainId                                                           AS chain_id,
    address                                                           AS pool_address,
    assetSymbol                                                       AS asset,
    totalDeposits,
    totalRagequits,
    if(totalDeposits > 0,
       totalRagequits / totalDeposits, 0)                             AS ragequit_count_rate,
    if(toFloat64OrZero(totalDepositValue) > 0,
       toFloat64OrZero(totalRagequitValue)
         / toFloat64OrZero(totalDepositValue), 0)                     AS ragequit_value_rate,
    toFloat64OrZero(totalRagequitValue) / pow(10, assetDecimals)      AS ragequit_amount,
    toFloat64OrZero(totalDepositValue) / pow(10, assetDecimals)       AS deposit_amount
FROM "Pool"
ORDER BY ragequit_value_rate DESC
