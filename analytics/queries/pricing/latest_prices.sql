-- Description: Most recent USD price per token, sourced from BSC
-- Uniswap V4 swaps (chainId 56). Use this as the read-side reference
-- for valuing on-pool balances across all chains.

SELECT
    chainId                              AS chain_id,
    symbol,
    token                                AS token_address,
    toFloat64(toString(priceUsd))        AS price_usd,
    refSymbol                            AS ref,
    blockNumber                          AS block,
    toDateTime(toUInt64(timestamp))      AS observed_at,
    poolId                               AS source_pool
FROM "LatestPrice"
ORDER BY symbol
