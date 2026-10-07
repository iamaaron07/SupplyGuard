# Blockchain Architecture

## Purpose

SupplyGuardLedger is the provenance layer for medicine batches. It records who handled a batch, when the event happened, and the hash associated with the event. It does not store medicine images or other large files on-chain.

## Contract Model

`SupplyGuardLedger.sol` contains:

- `Batch`: batch ID, product ID, manufacturer, creation timestamp, and existence flag.
- `LedgerRecord`: stage, actor wallet, timestamp, location, notes, hash, AI verdict/confidence, and the previous record ID.
- `createBatch`: manufacturer-only entry point that creates the first `MANUFACTURED` record.
- `recordSupplyChainEvent`: participant entry point for packaging, quality, warehouse, distributor, retailer, and correction events.
- `logVerification`: participant entry point for `REAL` or `FAKE` AI results and confidence from `0` to `10000` basis points.
- `getBatchHistory` and `getLatestRecord`: public history retrieval.

The event chain is append-only. A correction is another record; it cannot rewrite the original. Every record has a `previousRecordId`, and every nonzero data or verification hash is globally unique.

## Supply-Chain Flow

```text
Manufacturer -> Packaging -> Warehouse -> Distributor -> Retailer -> AI Verification
```

The deployer is initially authorized as both owner and participant. The owner can authorize manufacturers and participants. In a real deployment, these roles should be managed through audited identity and key-management processes.

## AI Integration

The Python inference pipeline produces a `REAL` or `FAKE` verdict and confidence. An integration layer should hash the image or canonical verification payload off-chain, then call `logVerification` with that `bytes32` hash. The image itself remains in application storage and is never sent to the contract.

## Development and Deployment

```bash
npm install
npm run compile
npm test
npx hardhat node
npm run deploy:local
```

For Sepolia, copy `.env.example` to `.env` and configure `SEPOLIA_RPC_URL`, `PRIVATE_KEY`, and optionally `ETHERSCAN_API_KEY`. The Hardhat config reads these values from `dotenv`; no credentials are committed or hard-coded.

The demo can be run against the in-process Hardhat network with:

```bash
npm run demo
```

## Security Considerations

- Solidity access modifiers prevent unauthorized batch creation and event writes.
- Hash uniqueness prevents replaying the same image or event payload.
- Verdicts are restricted to `REAL` and `FAKE`; confidence cannot exceed `100.00%`.
- No function deletes or updates a record, preserving the audit trail.
- On-chain hashes provide tamper evidence, but they do not prove that an off-chain image was honestly collected.
- The owner is a single administrative key in this student implementation. Production use should consider multisig, role separation, key rotation, monitoring, and an external audit.

## Current Boundary

The contract, scripts, and tests are implemented. A frontend and API that connect the YOLO inference result to the ledger are intentionally not implemented yet.