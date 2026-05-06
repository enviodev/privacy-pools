-- Description: Current anonymity-set size per pool, across all chains.
-- The leaf count IS the anonymity set — every prior commitment is a
-- candidate ancestor for any current withdrawal.

SELECT
    chainId            AS chain_id,
    address            AS pool_address,
    assetSymbol        AS asset,
    currentLeafCount   AS leaves,
    totalDeposits      AS deposits,
    totalWithdrawals   AS withdrawals,
    totalRagequits     AS ragequits,
    poolDied           AS dead,
    windDown           AS wind_down
FROM "Pool"
ORDER BY leaves DESC
