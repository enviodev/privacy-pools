-- Description: Per-chain fee withdrawals from the Entrypoint.

SELECT
    fw.chainId                                                        AS chain_id,
    fw.assetSymbol                                                    AS asset,
    fw.recipient                                                      AS recipient,
    toDateTime(toUInt64(fw.timestamp))                                AS withdrew_at,
    toFloat64OrZero(fw.amount) / pow(10, coalesce(p.assetDecimals, 18)) AS amount,
    fw.txHash                                                         AS tx
FROM "FeeWithdrawal" fw
LEFT JOIN "Pool" p
       ON p.chainId = fw.chainId AND p.asset = fw.asset
ORDER BY toUInt64(fw.timestamp) DESC
