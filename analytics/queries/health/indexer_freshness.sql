-- Description: True per-chain sync state.
--
-- "Indexer head" = the highest block envio has actually processed
-- (from envio_checkpoints — written on every batch, even when no
-- entity-emitting events fire). This is the right number to compare
-- against the chain's actual head block.
--
-- "Last event" = the most recent event that produced a Privacy Pools
-- entity row. Can be hours or days old even when the indexer is
-- caught up to chain head — the protocol just isn't busy.
--
-- Don't compute "lag" off `last_event_at`; lag = (chain head) − (indexer_head).

WITH
checkpoint AS (
    SELECT chain_id,
           max(block_number)        AS indexer_head,
           sum(events_processed)    AS events_processed
    FROM envio_checkpoints
    GROUP BY chain_id
),
last_ev AS (
    SELECT chainId,
           max(blockNumber)         AS last_event_block,
           max(toUInt64(timestamp)) AS last_event_ts
    FROM (
        SELECT chainId, blockNumber, timestamp FROM "Deposit"
        UNION ALL SELECT chainId, blockNumber, timestamp FROM "Withdrawal"
        UNION ALL SELECT chainId, blockNumber, timestamp FROM "Ragequit"
        UNION ALL SELECT chainId, blockNumber, timestamp FROM "MerkleLeaf"
    )
    GROUP BY chainId
)
SELECT
    c.chain_id                                                   AS chain_id,
    c.indexer_head                                               AS indexer_head,
    c.events_processed                                           AS events_processed,
    coalesce(le.last_event_block, 0)                             AS last_event_block,
    if(le.last_event_ts > 0, toDateTime(le.last_event_ts), NULL) AS last_event_at
FROM checkpoint c
LEFT JOIN last_ev le ON le.chainId = c.chain_id
ORDER BY c.chain_id
