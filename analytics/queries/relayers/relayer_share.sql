-- Description: Relayer market share, per chain.

SELECT
    chainId                                                              AS chain_id,
    relayer                                                              AS relayer,
    count()                                                              AS relays,
    uniqExact(recipient)                                                 AS unique_recipients,
    uniqExact(pool)                                                      AS unique_pools,
    sum(toFloat64OrZero(feeAmount))                                      AS fee_paid_raw_sum
FROM "Withdrawal"
WHERE isRelayed = true
GROUP BY chainId, relayer
ORDER BY chainId, relays DESC
