// BSC Uniswap V4 pricing — thin layer that derives USD prices for a small
// whitelist of tokens by listening to V4 Swap events on BSC mainnet.
//
// All BSC pricing tokens happen to be 18 decimals (Binance-Peg convention),
// which keeps the math simple. Ethereum-only assets (USDS, fxUSD, BOLD, ...)
// have no BSC-side liquidity and stay unpriced here — the analytics layer
// can treat known stables as $1.

import { BigDecimal } from "envio";

export type PricingMeta = { symbol: string; decimals: number; isStable: boolean };

// Lowercased BSC token addresses. Stables are treated as the $1 anchor;
// non-stables are priced when they appear in a pool with a stable.
export const BSC_PRICING_TOKENS: Record<string, PricingMeta> = {
  "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": { symbol: "WBNB",  decimals: 18, isStable: false },
  "0x55d398326f99059ff775485246999027b3197955": { symbol: "USDT",  decimals: 18, isStable: true  },
  "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": { symbol: "USDC",  decimals: 18, isStable: true  },
  "0x2170ed0880ac9a755fd29b2688956bd959f933f8": { symbol: "WETH",  decimals: 18, isStable: false },
  "0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c": { symbol: "BTCB",  decimals: 18, isStable: false },
  "0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3": { symbol: "DAI",   decimals: 18, isStable: true  },
};

export const BSC_WHITELIST_ADDRS: `0x${string}`[] = Object.keys(BSC_PRICING_TOKENS) as `0x${string}`[];

export function bscMeta(addr: string): PricingMeta | undefined {
  return BSC_PRICING_TOKENS[addr.toLowerCase()];
}

// Convert a Uniswap V4 sqrtPriceX96 + decimals into a token0-priced-in-token1
// (human-readable) BigDecimal. priceHuman = (sqrtP / 2^96)^2 * 10^(d0 - d1).
// We do everything in BigInt → string → BigDecimal to keep precision.
export function priceFromSqrtX96(
  sqrtPriceX96: bigint,
  decimals0: number,
  decimals1: number,
): BigDecimal {
  if (sqrtPriceX96 === 0n) return new BigDecimal(0);
  const Q192 = new BigDecimal(2).pow(192);
  // raw = (sqrtPriceX96)^2 / 2^192   -- token1 raw per token0 raw
  const sqrtBd = new BigDecimal(sqrtPriceX96.toString());
  const raw = sqrtBd.multipliedBy(sqrtBd).dividedBy(Q192);
  // human = raw * 10^(d0 - d1)   -- token1 (display) per token0 (display)
  const factor = new BigDecimal(10).pow(decimals0 - decimals1);
  return raw.multipliedBy(factor);
}

export type DerivedPrice = {
  pricedToken: string;     // address (lowercase) of the non-reference token
  pricedSymbol: string;
  refToken: string;
  refSymbol: string;
  priceUsd: BigDecimal;    // USD per pricedToken (display unit)
};

// Given a Swap on a pool whose currencies are both whitelisted, derive the
// USD price for the non-stable side. Returns null if neither currency is a
// stable anchor (we can't yet price tokens that only trade against other
// non-stables — could later derive transitively but that's out of scope).
export function derivePriceFromSwap(
  currency0: string,
  currency1: string,
  meta0: PricingMeta,
  meta1: PricingMeta,
  sqrtPriceX96: bigint,
): DerivedPrice | null {
  const priceToken1PerToken0 = priceFromSqrtX96(sqrtPriceX96, meta0.decimals, meta1.decimals);
  if (priceToken1PerToken0.isZero() || !priceToken1PerToken0.isFinite()) return null;

  if (meta1.isStable && !meta0.isStable) {
    return {
      pricedToken: currency0.toLowerCase(),
      pricedSymbol: meta0.symbol,
      refToken: currency1.toLowerCase(),
      refSymbol: meta1.symbol,
      priceUsd: priceToken1PerToken0,
    };
  }
  if (meta0.isStable && !meta1.isStable) {
    return {
      pricedToken: currency1.toLowerCase(),
      pricedSymbol: meta1.symbol,
      refToken: currency0.toLowerCase(),
      refSymbol: meta0.symbol,
      priceUsd: new BigDecimal(1).dividedBy(priceToken1PerToken0),
    };
  }
  // Both stable or both non-stable: nothing to do.
  return null;
}
