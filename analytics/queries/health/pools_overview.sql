-- Description: One row per pool (across all chains) with headline counters.

SELECT
    chainId                                                            AS chain_id,
    address                                                            AS pool_address,
    assetSymbol                                                        AS asset,
    assetDecimals                                                      AS decimals,
    registeredBlock                                                    AS registered_block,
    toDateTime(toUInt64(registeredAt))                                 AS registered_at,
    lastUpdatedBlock                                                   AS last_updated_block,
    toDateTime(toUInt64(lastUpdatedAt))                                AS last_updated_at,
    windDown,
    poolDied,
    totalDeposits,
    toFloat64OrZero(totalDepositValue) / pow(10, assetDecimals)        AS total_deposit_value,
    totalWithdrawals,
    toFloat64OrZero(totalWithdrawalValue) / pow(10, assetDecimals)     AS total_withdrawal_value,
    totalRagequits,
    toFloat64OrZero(totalRagequitValue) / pow(10, assetDecimals)       AS total_ragequit_value,
    currentLeafCount                                                   AS leaves
FROM "Pool"
ORDER BY chainId, total_deposit_value DESC
