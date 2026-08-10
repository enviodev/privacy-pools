export type AssetMeta = { symbol: string; decimals: number };

export const NATIVE = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";

// Asset metadata, keyed by chainId then lowercased token address.
const ASSETS_BY_CHAIN: Record<number, Record<string, AssetMeta>> = {
  1: { // Ethereum
    [NATIVE]:                                       { symbol: "ETH",    decimals: 18 },
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48":   { symbol: "USDC",   decimals: 6  },
    "0xdac17f958d2ee523a2206206994597c13d831ec7":   { symbol: "USDT",   decimals: 6  },
    "0x6b175474e89094c44da98b954eedeac495271d0f":   { symbol: "DAI",    decimals: 18 },
    "0xdc035d45d973e3ec169d2276ddab16f1e407384f":   { symbol: "USDS",   decimals: 18 },
    "0xa3931d71877c0e7a3148cb7eb4463524fec27fbd":   { symbol: "sUSDS",  decimals: 18 },
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599":   { symbol: "WBTC",   decimals: 8  },
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0":   { symbol: "wstETH", decimals: 18 },
    "0xcacd6fd266af91b8aed52accc382b4e165586e29":   { symbol: "frxUSD", decimals: 18 },
    "0x4c9edd5852cd905f086c759e8383e09bff1e68b3":   { symbol: "USDe",   decimals: 18 },
    "0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d":   { symbol: "USD1",   decimals: 18 },
    "0xdcee70654261af21c44c093c300ed3bb97b78192":   { symbol: "wOETH",  decimals: 18 },
    "0x085780639cc2cacd35e474e71f4d000e2405d8f6":   { symbol: "fxUSD",  decimals: 18 },
    "0x6440f144b7e50d6a8439336510312d2f54beb01d":   { symbol: "BOLD",   decimals: 18 },
  },
  10: { // Optimism
    [NATIVE]:                                       { symbol: "ETH",    decimals: 18 },
    "0x0b2c639c533813f4aa9d7837caf62653d097ff85":   { symbol: "USDC",   decimals: 6  },
  },
  56: { // BNB Smart Chain
    [NATIVE]:                                       { symbol: "BNB",    decimals: 18 },
    "0x55d398326f99059ff775485246999027b3197955":   { symbol: "USDT",   decimals: 18 },
  },
  42161: { // Arbitrum
    [NATIVE]:                                       { symbol: "ETH",    decimals: 18 },
    "0x252b965400862d94bda35fecf7ee0f204a53cc36":   { symbol: "yUSND",  decimals: 18 },
    "0xaf88d065e77c8cc2239327c5edb3a432268e5831":   { symbol: "USDC",   decimals: 6  },
  },
};

// Pool address (per chain) → asset address mapping. Used because the
// PrivacyPool.Deposited event only carries srcAddress (the pool); we
// look up which asset the pool holds.
const POOL_TO_ASSET_BY_CHAIN: Record<number, Record<string, string>> = {
  1: {
    "0xf241d57c6debae225c0f2e6ea1529373c9a9c9fb": NATIVE,
    "0x05e4dbd71b56861eed2aaa12d00a797f04b5d3c0": "0xdc035d45d973e3ec169d2276ddab16f1e407384f", // USDS
    "0xbbda2173cdfea1c3bd7f2908798f1265301d750c": "0xa3931d71877c0e7a3148cb7eb4463524fec27fbd", // sUSDS
    "0x1c31c03b8cb2ee674d0f11de77135536db828257": "0x6b175474e89094c44da98b954eedeac495271d0f", // DAI
    "0xb419c2867ab3cbc78921660cb95150d95a94ce86": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", // USDC
    "0xe859c0bd25f260baee534fb52e307d3b64d24572": "0xdac17f958d2ee523a2206206994597c13d831ec7", // USDT
    "0xf973f4b180a568157cd7a0e6006449139e6bfc32": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", // WBTC
    "0x1a604e9dfa0efdc7ffda378af16cb81243b61633": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", // wstETH
    "0xc6c769fac7aabeadd31a03fae5ca0ec5b4c50f84": "0xcacd6fd266af91b8aed52accc382b4e165586e29", // frxUSD
    "0xe6d36b33b00a7c0cb0c2a8d39d07e7db0c526abc": "0x4c9edd5852cd905f086c759e8383e09bff1e68b3", // USDe
    "0xc0a8bc0f4f982b4d4f1ffae8f4fccb58c9b29c98": "0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d", // USD1
    "0x7d2959bcfb936a84531518e8391ddba844e03ebe": "0xdcee70654261af21c44c093c300ed3bb97b78192", // wOETH
    "0xd14f4b36e1d1d98c218db782c49149876042bc56": "0x085780639cc2cacd35e474e71f4d000e2405d8f6", // fxUSD
    "0xb4b5fd38fd4788071d7287e3cb52948e0d10b23e": "0x6440f144b7e50d6a8439336510312d2f54beb01d", // BOLD
  },
  10: {
    "0x4626a182030d9e98b13f690fff3c443191a918ff": NATIVE,                                         // ETH
    "0xe4410f6827fa04ce096975d07a9924abb65316e3": "0x0b2c639c533813f4aa9d7837caf62653d097ff85",   // USDC
  },
  56: {
    "0x4626a182030d9e98b13f690fff3c443191a918ff": NATIVE,                                         // BNB
    "0x2ad9802dc8b9b4022aded1c6c8a7261970d84855": "0x55d398326f99059ff775485246999027b3197955",   // USDT
  },
  42161: {
    "0x4626a182030d9e98b13f690fff3c443191a918ff": NATIVE,                                         // ETH
    "0xa63e0bdc3a193d1e6e7c9be72cb502be4b7fc244": "0x252b965400862d94bda35fecf7ee0f204a53cc36",   // yUSND
    "0x3706e38af05bf0158bcdbb46239f8289980b093f": "0xaf88d065e77c8cc2239327c5edb3a432268e5831",   // USDC
  },
};

export function resolveAsset(addr: string): AssetMeta {
  const lc = addr.toLowerCase();
  return ASSETS_BY_CHAIN[chainId]?.[lc] ?? { symbol: "UNKNOWN", decimals: 18 };
}

export function resolvePoolAsset(
  poolAddr: string,
): { asset: string; meta: AssetMeta } {
  const lc = poolAddr.toLowerCase();
  const asset = POOL_TO_ASSET_BY_CHAIN[chainId]?.[lc] ?? NATIVE;
  return { asset, meta: resolveAsset(chainId, asset) };
}
