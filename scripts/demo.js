const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const EVENT_NAMES = [
  "MANUFACTURED",
  "PACKAGED",
  "QUALITY_CHECK",
  "WAREHOUSE_RECEIVED",
  "DISTRIBUTOR_RECEIVED",
  "RETAILER_RECEIVED",
  "VERIFIED",
  "FLAGGED_FAKE",
  "CORRECTION",
];

const VERDICT_NAMES = ["NONE", "REAL", "FAKE"];

function confidenceText(confidenceBps) {
  return `${(Number(confidenceBps) / 100).toFixed(2)}%`;
}

async function main() {
  const [owner, manufacturer, packaging, warehouse, distributor, aiVerifier] =
    await hre.ethers.getSigners();

  const deploymentPath = path.join(__dirname, "..", "runs", "blockchain", "deployment.json");
  let ledger;
  if (process.env.SUPPLYGUARD_CONTRACT_ADDRESS) {
    ledger = await hre.ethers.getContractAt("SupplyGuardLedger", process.env.SUPPLYGUARD_CONTRACT_ADDRESS);
  } else if (fs.existsSync(deploymentPath)) {
    const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
    ledger = await hre.ethers.getContractAt("SupplyGuardLedger", deployment.address);
  } else {
    const SupplyGuardLedger = await hre.ethers.getContractFactory("SupplyGuardLedger");
    ledger = await SupplyGuardLedger.deploy();
    await ledger.waitForDeployment();
  }

  await ledger.setManufacturerAuthorization(manufacturer.address, true);
  for (const account of [packaging, warehouse, distributor, aiVerifier]) {
    await ledger.setParticipantAuthorization(account.address, true);
  }

  const batchId = "SG-BATCH-001";
  const productId = "MED-PARACETAMOL-500";

  await ledger
    .connect(manufacturer)
    .createBatch(
      batchId,
      productId,
      "Manufacturer Facility",
      hre.ethers.id("SG-BATCH-001:manufactured"),
      "Batch manufactured"
    );
  await ledger
    .connect(packaging)
    .recordSupplyChainEvent(
      batchId,
      1,
      "Packaging Line A",
      hre.ethers.id("SG-BATCH-001:packaged"),
      "Batch packaged"
    );
  await ledger
    .connect(warehouse)
    .recordSupplyChainEvent(
      batchId,
      3,
      "Central Warehouse",
      hre.ethers.id("SG-BATCH-001:warehouse"),
      "Batch received by warehouse"
    );
  await ledger
    .connect(distributor)
    .recordSupplyChainEvent(
      batchId,
      4,
      "North Distributor",
      hre.ethers.id("SG-BATCH-001:distributor"),
      "Batch received by distributor"
    );
  await ledger
    .connect(aiVerifier)
    .logVerification(
      batchId,
      hre.ethers.id("SG-BATCH-001:image-hash:FAKE:9667"),
      2,
      9667,
      "AI Verification Station",
      "YOLOv8 classified the package image as FAKE"
    );

  const history = await ledger.getBatchHistory(batchId);

  console.log("================================");
  console.log("SUPPLYGUARD BATCH HISTORY");
  console.log("================================");
  console.log(`Batch: ${batchId}`);
  console.log(`Product: ${productId}`);
  console.log("");

  history.forEach((record, index) => {
    console.log(`${index + 1}. ${EVENT_NAMES[Number(record.eventType)]}`);
    console.log(`   Actor: ${record.actor}`);
    console.log(`   Location: ${record.location}`);
    console.log(`   Hash: ${record.dataHash}`);
    if (Number(record.verdict) !== 0) {
      console.log(`   Verdict: ${VERDICT_NAMES[Number(record.verdict)]}`);
      console.log(`   Confidence: ${confidenceText(record.confidenceBps)}`);
    }
    console.log(`   Notes: ${record.notes}`);
    console.log("");
  });

  console.log("================================");
  console.log("History is append-only: no delete or overwrite function exists.");
  console.log("================================");

  void owner;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

