import { indexer } from "envio";
import { resolveAsset, resolvePoolAsset } from "./assets.js";
import { BSC_PRICING_TOKENS, derivePriceFromSwap } from "./v4Pricing.js";
import { BSC_V4_PRICING_POOL_IDS } from "./v4PoolIds.js";
import { V4_POOL_META } from "./v4PoolMeta.js";

const lc = (s: string) => s.toLowerCase();
const poolKey = (chainId: number, address: string) => `${chainId}_${lc(address)}`;
const eventId = (chainId: number, txHash: string, logIndex: number) =>
  `${chainId}_${txHash}-${logIndex}`;

async function getOrInitPool(
  context: any,
  chainId: number,
  poolAddr: string,
  ts: bigint,
  block: number,
): Promise<any> {
  const id = poolKey(chainId, poolAddr);
  const existing = await context.Pool.get(id);
  if (existing) return existing;
  const { asset, meta } = resolvePoolAsset(chainId, poolAddr);
  const fresh = {
    id,
    chainId,
    address: lc(poolAddr),
    scope: 0n,
    asset,
    assetSymbol: meta.symbol,
    assetDecimals: meta.decimals,
    minimumDepositAmount: 0n,
    vettingFeeBPS: 0n,
    maxRelayFeeBPS: 0n,
    registeredAt: ts,
    registeredBlock: block,
    lastUpdatedAt: ts,
    lastUpdatedBlock: block,
    windDown: false,
    poolDied: false,
    totalDeposits: 0,
    totalDepositValue: 0n,
    totalWithdrawals: 0,
    totalWithdrawalValue: 0n,
    totalRagequits: 0,
    totalRagequitValue: 0n,
    currentLeafCount: 0,
    currentRoot: 0n,
  };
  context.Pool.set(fresh);
  return fresh;
}

async function bumpAccount(
  context: any,
  addr: string,
  chainId: number,
  ts: bigint,
  block: number,
  field: "depositCount" | "withdrawalCount" | "ragequitCount",
) {
  const id = lc(addr);
  const existing = await context.Account.get(id);
  if (existing) {
    context.Account.set({
      ...existing,
      [field]: existing[field] + 1,
      lastSeen: ts > existing.lastSeen ? ts : existing.lastSeen,
      lastSeenBlock: ts > existing.lastSeen ? block : existing.lastSeenBlock,
    });
  } else {
    context.Account.set({
      id,
      firstSeen: ts,
      firstSeenBlock: block,
      firstSeenChain: chainId,
      lastSeen: ts,
      lastSeenBlock: block,
      depositCount: field === "depositCount" ? 1 : 0,
      withdrawalCount: field === "withdrawalCount" ? 1 : 0,
      ragequitCount: field === "ragequitCount" ? 1 : 0,
    });
  }
}

// ---------- Entrypoint: pool lifecycle ----------

indexer.onEvent({ contract: "Entrypoint", event: "PoolRegistered" }, async ({ event, context }) => {
  const chainId = event.chainId;
  const id = poolKey(chainId, event.params._pool);
  const meta = resolveAsset(chainId, event.params._asset);
  const ts = BigInt(event.block.timestamp);
  const existing = await context.Pool.get(id);
  context.Pool.set({
    ...(existing ?? {
      minimumDepositAmount: 0n,
      vettingFeeBPS: 0n,
      maxRelayFeeBPS: 0n,
      windDown: false,
      poolDied: false,
      totalDeposits: 0,
      totalDepositValue: 0n,
      totalWithdrawals: 0,
      totalWithdrawalValue: 0n,
      totalRagequits: 0,
      totalRagequitValue: 0n,
      currentLeafCount: 0,
      currentRoot: 0n,
    }),
    id,
    chainId,
    address: lc(event.params._pool),
    scope: event.params._scope,
    asset: lc(event.params._asset),
    assetSymbol: meta.symbol,
    assetDecimals: meta.decimals,
    registeredAt: ts,
    registeredBlock: event.block.number,
    lastUpdatedAt: ts,
    lastUpdatedBlock: event.block.number,
  });
});

indexer.onEvent({ contract: "Entrypoint", event: "PoolConfigurationUpdated" }, async ({ event, context }) => {
  const pool = await getOrInitPool(context, event.chainId, event.params._pool, BigInt(event.block.timestamp), event.block.number);
  context.Pool.set({
    ...pool,
    minimumDepositAmount: event.params._newMinimumDepositAmount,
    vettingFeeBPS: event.params._newVettingFeeBPS,
    maxRelayFeeBPS: event.params._newMaxRelayFeeBPS,
    lastUpdatedAt: BigInt(event.block.timestamp),
    lastUpdatedBlock: event.block.number,
  });
});

indexer.onEvent({ contract: "Entrypoint", event: "PoolWindDown" }, async ({ event, context }) => {
  const pool = await getOrInitPool(context, event.chainId, event.params._pool, BigInt(event.block.timestamp), event.block.number);
  context.Pool.set({
    ...pool,
    windDown: true,
    lastUpdatedAt: BigInt(event.block.timestamp),
    lastUpdatedBlock: event.block.number,
  });
});

indexer.onEvent({ contract: "Entrypoint", event: "PoolRemoved" }, async ({ event, context }) => {
  const pool = await getOrInitPool(context, event.chainId, event.params._pool, BigInt(event.block.timestamp), event.block.number);
  context.Pool.set({
    ...pool,
    windDown: true,
    lastUpdatedAt: BigInt(event.block.timestamp),
    lastUpdatedBlock: event.block.number,
  });
});

// ---------- Entrypoint: ASP root + fees ----------

indexer.onEvent({ contract: "Entrypoint", event: "RootUpdated" }, async ({ event, context }) => {
  context.AssociationSetRoot.set({
    id: eventId(event.chainId, event.transaction.hash, event.logIndex),
    chainId: event.chainId,
    root: event.params._root,
    ipfsCID: event.params._ipfsCID,
    rootTimestamp: event.params._timestamp,
    blockNumber: event.block.number,
    blockTimestamp: BigInt(event.block.timestamp),
    txHash: event.transaction.hash,
  });
});

indexer.onEvent({ contract: "Entrypoint", event: "FeesWithdrawn" }, async ({ event, context }) => {
  const meta = resolveAsset(event.chainId, event.params._asset);
  context.FeeWithdrawal.set({
    id: eventId(event.chainId, event.transaction.hash, event.logIndex),
    chainId: event.chainId,
    asset: lc(event.params._asset),
    assetSymbol: meta.symbol,
    recipient: lc(event.params._recipient),
    amount: event.params._amount,
    timestamp: BigInt(event.block.timestamp),
    blockNumber: event.block.number,
    txHash: event.transaction.hash,
  });
});

// ---------- Deposit pair ----------

indexer.onEvent({ contract: "PrivacyPool", event: "Deposited" }, async ({ event, context }) => {
  const chainId = event.chainId;
  const poolAddr = lc(event.srcAddress);
  const ts = BigInt(event.block.timestamp);
  const pool = await getOrInitPool(context, chainId, poolAddr, ts, event.block.number);

  const id = eventId(chainId, event.transaction.hash, event.logIndex);
  context.Deposit.set({
    id,
    chainId,
    pool: pool.id,
    poolAddress: poolAddr,
    assetSymbol: pool.assetSymbol,
    depositor: lc(event.params._depositor),
    commitment: event.params._commitment,
    label: event.params._label,
    value: event.params._value,
    precommitmentHash: event.params._precommitmentHash,
    entrypointAmount: undefined,
    entrypointDepositor: undefined,
    vettingFee: undefined,
    blockNumber: event.block.number,
    timestamp: ts,
    txHash: event.transaction.hash,
    txFrom: event.transaction.from ?? undefined,
  });

  context.Pool.set({
    ...pool,
    totalDeposits: pool.totalDeposits + 1,
    totalDepositValue: pool.totalDepositValue + event.params._value,
    lastUpdatedAt: ts,
    lastUpdatedBlock: event.block.number,
  });

  await bumpAccount(context, event.params._depositor, chainId, ts, event.block.number, "depositCount");
});

indexer.onEvent({ contract: "Entrypoint", event: "Deposited" }, async ({ event, context }) => {
  const poolId = poolKey(event.chainId, event.params._pool);
  const matches = await context.Deposit.getWhere({ txHash: { _eq: event.transaction.hash } });
  for (const dep of matches) {
    if (dep.pool === poolId && dep.entrypointAmount === undefined) {
      const fee = event.params._amount - dep.value;
      context.Deposit.set({
        ...dep,
        entrypointAmount: event.params._amount,
        entrypointDepositor: lc(event.params._depositor),
        vettingFee: fee >= 0n ? fee : 0n,
      });
      return;
    }
  }
});

// ---------- Withdrawal pair ----------

indexer.onEvent({ contract: "PrivacyPool", event: "Withdrawn" }, async ({ event, context }) => {
  const chainId = event.chainId;
  const poolAddr = lc(event.srcAddress);
  const ts = BigInt(event.block.timestamp);
  const pool = await getOrInitPool(context, chainId, poolAddr, ts, event.block.number);

  context.Withdrawal.set({
    id: eventId(chainId, event.transaction.hash, event.logIndex),
    chainId,
    pool: pool.id,
    poolAddress: poolAddr,
    assetSymbol: pool.assetSymbol,
    processooor: lc(event.params._processooor),
    withdrawnValue: event.params._value,
    spentNullifier: event.params._spentNullifier,
    newCommitment: event.params._newCommitment,
    isRelayed: false,
    relayer: undefined,
    recipient: undefined,
    feeAmount: undefined,
    blockNumber: event.block.number,
    timestamp: ts,
    txHash: event.transaction.hash,
  });

  context.Pool.set({
    ...pool,
    totalWithdrawals: pool.totalWithdrawals + 1,
    totalWithdrawalValue: pool.totalWithdrawalValue + event.params._value,
    lastUpdatedAt: ts,
    lastUpdatedBlock: event.block.number,
  });

  await bumpAccount(context, event.params._processooor, chainId, ts, event.block.number, "withdrawalCount");
});

indexer.onEvent({ contract: "Entrypoint", event: "WithdrawalRelayed" }, async ({ event, context }) => {
  const matches = await context.Withdrawal.getWhere({ txHash: { _eq: event.transaction.hash } });
  for (const w of matches) {
    if (w.chainId === event.chainId && !w.isRelayed) {
      context.Withdrawal.set({
        ...w,
        isRelayed: true,
        relayer: lc(event.params._relayer),
        recipient: lc(event.params._recipient),
        feeAmount: event.params._feeAmount,
      });
      return;
    }
  }
});

// ---------- Ragequit / leaves / death ----------

indexer.onEvent({ contract: "PrivacyPool", event: "Ragequit" }, async ({ event, context }) => {
  const chainId = event.chainId;
  const poolAddr = lc(event.srcAddress);
  const ts = BigInt(event.block.timestamp);
  const pool = await getOrInitPool(context, chainId, poolAddr, ts, event.block.number);

  context.Ragequit.set({
    id: eventId(chainId, event.transaction.hash, event.logIndex),
    chainId,
    pool: pool.id,
    poolAddress: poolAddr,
    assetSymbol: pool.assetSymbol,
    ragequitter: lc(event.params._ragequitter),
    commitment: event.params._commitment,
    label: event.params._label,
    value: event.params._value,
    blockNumber: event.block.number,
    timestamp: ts,
    txHash: event.transaction.hash,
  });

  context.Pool.set({
    ...pool,
    totalRagequits: pool.totalRagequits + 1,
    totalRagequitValue: pool.totalRagequitValue + event.params._value,
    lastUpdatedAt: ts,
    lastUpdatedBlock: event.block.number,
  });

  await bumpAccount(context, event.params._ragequitter, chainId, ts, event.block.number, "ragequitCount");
});

indexer.onEvent({ contract: "PrivacyPool", event: "LeafInserted" }, async ({ event, context }) => {
  const chainId = event.chainId;
  const poolAddr = lc(event.srcAddress);
  const ts = BigInt(event.block.timestamp);
  const pool = await getOrInitPool(context, chainId, poolAddr, ts, event.block.number);
  const idx = Number(event.params._index);

  context.MerkleLeaf.set({
    id: `${pool.id}-${idx}`,
    chainId,
    pool: pool.id,
    poolAddress: poolAddr,
    index: idx,
    leaf: event.params._leaf,
    root: event.params._root,
    blockNumber: event.block.number,
    timestamp: ts,
    txHash: event.transaction.hash,
  });

  context.Pool.set({
    ...pool,
    currentLeafCount: idx + 1,
    currentRoot: event.params._root,
    lastUpdatedAt: ts,
    lastUpdatedBlock: event.block.number,
  });
});

indexer.onEvent({ contract: "PrivacyPool", event: "PoolDied" }, async ({ event, context }) => {
  const pool = await getOrInitPool(context, event.chainId, event.srcAddress, BigInt(event.block.timestamp), event.block.number);
  context.Pool.set({
    ...pool,
    poolDied: true,
    lastUpdatedAt: BigInt(event.block.timestamp),
    lastUpdatedBlock: event.block.number,
  });
});

// ---------- Uniswap V4 pricing (BSC) ----------
// Head-only: V4 contract `start_block` is set near BSC head so we don't
// backfill years of history just to read the current price. Pool
// metadata is hardcoded (snapshot of discovered pools) so we don't
// even need an Initialize handler.

indexer.onEvent(
  {
    contract: "UniswapV4PoolManager",
    event: "Swap",
    // Hard filter to known pricing pools — pre-discovered.
    where: { params: { id: BSC_V4_PRICING_POOL_IDS } },
  },
  async ({ event, context }) => {
    const poolId = event.params.id.toLowerCase();
    const meta = V4_POOL_META[poolId];
    if (!meta) return; // unknown pool (filter slipped through)

    const m0 = BSC_PRICING_TOKENS[meta.currency0];
    const m1 = BSC_PRICING_TOKENS[meta.currency1];
    if (!m0 || !m1) return;

    const derived = derivePriceFromSwap(
      meta.currency0,
      meta.currency1,
      m0,
      m1,
      event.params.sqrtPriceX96,
    );
    if (!derived) return;

    const ts = BigInt(event.block.timestamp);
    context.TokenPrice.set({
      id: `${event.chainId}_${event.transaction.hash}-${event.logIndex}_${derived.pricedToken}`,
      chainId: event.chainId,
      token: derived.pricedToken,
      symbol: derived.pricedSymbol,
      priceUsd: derived.priceUsd,
      refToken: derived.refToken,
      refSymbol: derived.refSymbol,
      poolId,
      blockNumber: event.block.number,
      timestamp: ts,
      txHash: event.transaction.hash,
    });

    context.LatestPrice.set({
      id: `${event.chainId}_${derived.pricedToken}`,
      chainId: event.chainId,
      token: derived.pricedToken,
      symbol: derived.pricedSymbol,
      priceUsd: derived.priceUsd,
      blockNumber: event.block.number,
      timestamp: ts,
      poolId,
      refSymbol: derived.refSymbol,
    });
  },
);
