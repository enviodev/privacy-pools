-- Description: Mirror-deposit detector — third-party obfuscation pattern.
-- Multi-chain: same chain only, joining via chainId-scoped Pool.id.
--
-- Parameters:
--   {{window}} - lag seconds upper bound (default: 1800)

SELECT
    w.chainId                                                  AS chain_id,
    w.poolAddress                                              AS pool_address,
    w.assetSymbol                                              AS asset,
    toFloat64OrZero(w.withdrawnValue) / pow(10, p.assetDecimals) AS amount,
    coalesce(w.recipient, w.processooor)                       AS withdrawal_recipient,
    w.txHash                                                   AS withdraw_tx,
    toDateTime(toUInt64(w.timestamp))                          AS withdrew_at,
    d.depositor                                                AS mirror_depositor,
    d.txHash                                                   AS mirror_deposit_tx,
    toDateTime(toUInt64(d.timestamp))                          AS deposited_at,
    (toUInt64(d.timestamp) - toUInt64(w.timestamp))            AS lag_seconds
FROM "Withdrawal" w
JOIN "Deposit" d
  ON  d.pool                 = w.pool
 AND  d.value                = w.withdrawnValue
 AND  toUInt64(d.timestamp) >= toUInt64(w.timestamp)
 AND  toUInt64(d.timestamp) <= toUInt64(w.timestamp) + {{window}}
 AND  d.depositor            != coalesce(w.recipient, '')
 AND  d.depositor            != coalesce(w.processooor, '')
JOIN "Pool" p ON p.id = w.pool
ORDER BY toUInt64(w.timestamp)
