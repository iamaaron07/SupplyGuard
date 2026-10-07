const hre = require("hardhat");
const crypto = require("crypto");

async function main() {
  const required = ["SUPPLYGUARD_CONTRACT_ADDRESS", "SUPPLYGUARD_BATCH_ID", "SUPPLYGUARD_VERIFICATION_HASH", "SUPPLYGUARD_VERDICT"];
  for (const name of required) {
    if (!process.env[name]) throw new Error(`${name} is required`);
  }
  const [verifier] = await hre.ethers.getSigners();
  const ledger = await hre.ethers.getContractAt("SupplyGuardLedger", process.env.SUPPLYGUARD_CONTRACT_ADDRESS, verifier);
  const verdict = process.env.SUPPLYGUARD_VERDICT.toUpperCase() === "FAKE" ? 2 : 1;
  const hash = process.env.SUPPLYGUARD_VERIFICATION_HASH.startsWith("0x")
    ? process.env.SUPPLYGUARD_VERIFICATION_HASH
    : `0x${crypto.createHash("sha256").update(process.env.SUPPLYGUARD_VERIFICATION_HASH).digest("hex")}`;
  const tx = await ledger.logVerification(
    process.env.SUPPLYGUARD_BATCH_ID,
    hash,
    verdict,
    Number(process.env.SUPPLYGUARD_CONFIDENCE_BPS || 0),
    process.env.SUPPLYGUARD_LOCATION || "AI Verification Station",
    "Recorded by SupplyGuard AI API"
  );
  await tx.wait();
  console.log(`Transaction hash: ${tx.hash}`);
}

main().catch((error) => { console.error(error.message || error); process.exitCode = 1; });