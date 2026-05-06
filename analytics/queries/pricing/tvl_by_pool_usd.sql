-- Description: USD-valued TVL per pool. Uses BSC V4 LatestPrice for
-- tokens we can price (BNB → WBNB, ETH → WETH, BTC → BTCB, stables at
-- $1) and falls back to $1 for known stables. Tokens we can't price
-- show price=NULL and tvl_usd=NULL.
--
-- Symbol mapping rule:
--   * Stablecoin symbols (USDS, sUSDS, DAI, USDC, USDT, frxUSD, USDe,
--     USD1, fxUSD, BSCUSD, yUSND, BOLD) are pegged to $1 by convention.
--   * ETH on any chain → look up WETH price.
--   * BNB → WBNB price.
--   * WBTC → BTCB price.
--   * wstETH/wOETH → ETH price (rough; ignores the staking yield discount).

WITH stable_set AS (
    SELECT * FROM (
        SELECT 'USDC' AS s UNION ALL SELECT 'USDT' UNION ALL SELECT 'DAI'
        UNION ALL SELECT 'USDS' UNION ALL SELECT 'sUSDS' UNION ALL SELECT 'frxUSD'
        UNION ALL SELECT 'USDe' UNION ALL SELECT 'USD1' UNION ALL SELECT 'fxUSD'
        UNION ALL SELECT 'BOLD' UNION ALL SELECT 'yUSND'
    )
),
priced AS (
    SELECT symbol, max(toFloat64(toString(priceUsd))) AS price_usd
    FROM "LatestPrice"
    GROUP BY symbol
),
mapped AS (
    SELECT
        p.chainId,
        p.address                                                              AS pool_address,
        p.assetSymbol                                                          AS asset,
        p.assetDecimals,
        toFloat64OrZero(p.totalDepositValue) / pow(10, p.assetDecimals)        AS deposited,
        toFloat64OrZero(p.totalWithdrawalValue) / pow(10, p.assetDecimals)     AS withdrawn,
        toFloat64OrZero(p.totalRagequitValue) / pow(10, p.assetDecimals)       AS ragequit,
        (toFloat64OrZero(p.totalDepositValue)
            - toFloat64OrZero(p.totalWithdrawalValue)
            - toFloat64OrZero(p.totalRagequitValue)) / pow(10, p.assetDecimals)  AS tvl_native,
        if(p.assetSymbol IN (SELECT s FROM stable_set),
           1.0,
        if(p.assetSymbol IN ('ETH','wstETH','wOETH'), (SELECT price_usd FROM priced WHERE symbol = 'WETH'),
        if(p.assetSymbol = 'BNB',  (SELECT price_usd FROM priced WHERE symbol = 'WBNB'),
        if(p.assetSymbol = 'WBTC', (SELECT price_usd FROM priced WHERE symbol = 'BTCB'),
           NULL))))                                                              AS price_usd
    FROM "Pool" p
)
SELECT
    chainId       AS chain_id,
    pool_address,
    asset,
    deposited,
    withdrawn,
    ragequit,
    tvl_native,
    price_usd,
    tvl_native * price_usd AS tvl_usd
FROM mapped
ORDER BY tvl_usd DESC NULLS LAST
