-- Description: ASP root-update cadence per chain.

SELECT
    chainId                                                        AS chain_id,
    toDateTime(toUInt64(rootTimestamp))                            AS root_at,
    toDateTime(toUInt64(blockTimestamp))                           AS chain_at,
    blockNumber                                                    AS block,
    substr(toString(root), 1, 12)                                  AS root_prefix,
    ipfsCID,
    txHash
FROM "AssociationSetRoot"
ORDER BY toUInt64(rootTimestamp) DESC
LIMIT 200
