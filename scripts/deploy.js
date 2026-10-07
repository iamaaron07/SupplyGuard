const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying SupplyGuardLedger...");
  console.log(`Network: ${hre.network.name}`);

  const SupplyGuardLedger = await hre.ethers.getContractFactory("SupplyGuardLedger");
  const ledger = await SupplyGuardLedger.deploy();
  const deploymentTx = ledger.deploymentTransaction();
  await ledger.waitForDeployment();

  const address = await ledger.getAddress();
  const deploymentPath = path.join(__dirname, "..", "runs", "blockchain", "deployment.json");
  fs.mkdirSync(path.dirname(deploymentPath), { recursive: true });
  fs.writeFileSync(deploymentPath, JSON.stringify({ network: hre.network.name, address }, null, 2));
  console.log("================================");
  console.log("SupplyGuardLedger deployed");
  console.log("================================");
  console.log(`Address: ${address}`);
  console.log(`Transaction hash: ${deploymentTx.hash}`);
  console.log("================================");

  if (hre.network.name === "sepolia") {
    console.log("Optional verification command:");
    console.log(`npx hardhat verify --network sepolia ${address}`);
  }
}

main().catch((error) => {
  console.error("Deployment failed:");
  console.error(error);
  process.exitCode = 1;
});

