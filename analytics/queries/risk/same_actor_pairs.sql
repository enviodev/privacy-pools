-- Description: Same-amount, time-windowed deposit→withdrawal pairs —
-- the headline linkability heuristic, multi-chain edition.
--
-- Parameters:
--   {{min_gap}} - minimum gap seconds (default: 60)
--   {{max_gap}} - maximum gap seconds (default: 7200)

SELECT
    d.chainId                                                  AS chain_id,
    d.poolAddress                                              AS pool_address,
    d.assetSymbol                                              AS asset,
    toFloat64OrZero(d.value) / pow(10, p.assetDecimals)        AS amount,
    d.depositor                                                AS depositor,
    d.txHash                                                   AS deposit_tx,
    toDateTime(toUInt64(d.timestamp))                          AS deposit_at,
    coalesce(w.recipient, w.processooor)                       AS withdrawal_recipient,
    w.txHash                                                   AS withdrawal_tx,
    toDateTime(toUInt64(w.timestamp))                          AS withdrawal_at,
    (toUInt64(w.timestamp) - toUInt64(d.timestamp))            AS gap_seconds
FROM "Deposit" d
JOIN "Withdrawal" w
  ON  w.pool                = d.pool                          -- chainId-scoped Pool.id
 AND  w.withdrawnValue      = d.value
 AND  toUInt64(w.timestamp) >  toUInt64(d.timestamp)
 AND (toUInt64(w.timestamp) -  toUInt64(d.timestamp)) BETWEEN {{min_gap}} AND {{max_gap}}
JOIN "Pool" p ON p.id = d.pool
ORDER BY toUInt64(d.timestamp)
