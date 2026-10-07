const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

const EventType = {
  MANUFACTURED: 0,
  PACKAGED: 1,
  QUALITY_CHECK: 2,
  WAREHOUSE_RECEIVED: 3,
  DISTRIBUTOR_RECEIVED: 4,
  RETAILER_RECEIVED: 5,
  VERIFIED: 6,
  FLAGGED_FAKE: 7,
  CORRECTION: 8,
};

const Verdict = {
  NONE: 0,
  REAL: 1,
  FAKE: 2,
};

describe("SupplyGuardLedger", function () {
  async function deployFixture() {
    const [owner, manufacturer, warehouse, distributor, verifier, unauthorized] =
      await ethers.getSigners();
    const Ledger = await ethers.getContractFactory("SupplyGuardLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();

    await ledger.setManufacturerAuthorization(manufacturer.address, true);
    await ledger.setParticipantAuthorization(warehouse.address, true);
    await ledger.setParticipantAuthorization(distributor.address, true);
    await ledger.setParticipantAuthorization(verifier.address, true);

    return { ledger, owner, manufacturer, warehouse, distributor, verifier, unauthorized };
  }

  async function createBatch(ledger, manufacturer, batchId = "SG-BATCH-001") {
    await ledger
      .connect(manufacturer)
      .createBatch(
        batchId,
        "MED-PARACETAMOL-500",
        "Manufacturer Facility",
        ethers.id(`${batchId}:manufactured`),
        "Created batch"
      );
  }

  it("deploys and authorizes the deployer", async function () {
    const { ledger, owner } = await deployFixture();
    expect(await ledger.owner()).to.equal(owner.address);
    expect(await ledger.authorizedManufacturers(owner.address)).to.equal(true);
    expect(await ledger.authorizedParticipants(owner.address)).to.equal(true);
  });

  it("creates a new batch and emits events", async function () {
    const { ledger, manufacturer } = await deployFixture();
    await expect(
      ledger
        .connect(manufacturer)
        .createBatch(
          "SG-BATCH-001",
          "MED-PARACETAMOL-500",
          "Manufacturer Facility",
          ethers.id("batch-create"),
          "Created batch"
        )
    )
      .to.emit(ledger, "BatchCreated")
      .withArgs("SG-BATCH-001", "MED-PARACETAMOL-500", manufacturer.address, anyValue);

    const batch = await ledger.getBatch("SG-BATCH-001");
    expect(batch.manufacturer).to.equal(manufacturer.address);
    expect(await ledger.getBatchHistoryLength("SG-BATCH-001")).to.equal(1);
  });

  it("records supply-chain events with actor addresses and timestamps", async function () {
    const { ledger, manufacturer, warehouse } = await deployFixture();
    await createBatch(ledger, manufacturer);

    await expect(
      ledger
        .connect(warehouse)
        .recordSupplyChainEvent(
          "SG-BATCH-001",
          EventType.WAREHOUSE_RECEIVED,
          "Central Warehouse",
          ethers.id("warehouse-received"),
          "Warehouse received batch"
        )
    )
      .to.emit(ledger, "SupplyChainEventRecorded")
      .withArgs(
        "SG-BATCH-001",
        anyValue,
        EventType.WAREHOUSE_RECEIVED,
        warehouse.address,
        anyValue,
        ethers.id("warehouse-received")
      );

    const history = await ledger.getBatchHistory("SG-BATCH-001");
    expect(history.length).to.equal(2);
    expect(history[1].actor).to.equal(warehouse.address);
    expect(history[1].eventType).to.equal(EventType.WAREHOUSE_RECEIVED);
    expect(history[1].timestamp).to.be.greaterThan(0);
    expect(history[1].previousRecordId).to.equal(history[0].recordId);
  });

  it("stores REAL verification records", async function () {
    const { ledger, manufacturer, verifier } = await deployFixture();
    await createBatch(ledger, manufacturer);

    await expect(
      ledger
        .connect(verifier)
        .logVerification(
          "SG-BATCH-001",
          ethers.id("real-verification"),
          Verdict.REAL,
          9700,
          "AI Station",
          "AI classified image as REAL"
        )
    ).to.emit(ledger, "VerificationLogged");

    const latest = await ledger.getLatestRecord("SG-BATCH-001");
    expect(latest.eventType).to.equal(EventType.VERIFIED);
    expect(latest.verdict).to.equal(Verdict.REAL);
    expect(latest.confidenceBps).to.equal(9700);
  });

  it("stores FAKE verification records and emits fake flag event", async function () {
    const { ledger, manufacturer, verifier } = await deployFixture();
    await createBatch(ledger, manufacturer);

    await expect(
      ledger
        .connect(verifier)
        .logVerification(
          "SG-BATCH-001",
          ethers.id("fake-verification"),
          Verdict.FAKE,
          9667,
          "AI Station",
          "AI classified image as FAKE"
        )
    ).to.emit(ledger, "FakeMedicineFlagged");

    const latest = await ledger.getLatestRecord("SG-BATCH-001");
    expect(latest.eventType).to.equal(EventType.FLAGGED_FAKE);
    expect(latest.verdict).to.equal(Verdict.FAKE);
    expect(latest.confidenceBps).to.equal(9667);
  });

  it("rejects invalid verdicts and invalid confidence scores", async function () {
    const { ledger, manufacturer, verifier } = await deployFixture();
    await createBatch(ledger, manufacturer);

    await expect(
      ledger
        .connect(verifier)
        .logVerification(
          "SG-BATCH-001",
          ethers.id("invalid-verdict"),
          Verdict.NONE,
          9000,
          "AI Station",
          "Invalid verdict"
        )
    ).to.be.revertedWith("Invalid verdict");

    await expect(
      ledger
        .connect(verifier)
        .logVerification(
          "SG-BATCH-001",
          ethers.id("invalid-confidence"),
          Verdict.REAL,
          10001,
          "AI Station",
          "Invalid confidence"
        )
    ).to.be.revertedWith("Invalid confidence");
  });

  it("rejects duplicate hashes", async function () {
    const { ledger, manufacturer, warehouse } = await deployFixture();
    await createBatch(ledger, manufacturer);

    const duplicateHash = ethers.id("duplicate-hash");
    await ledger
      .connect(warehouse)
      .recordSupplyChainEvent(
        "SG-BATCH-001",
        EventType.WAREHOUSE_RECEIVED,
        "Central Warehouse",
        duplicateHash,
        "First record"
      );

    await expect(
      ledger
        .connect(warehouse)
        .recordSupplyChainEvent(
          "SG-BATCH-001",
          EventType.DISTRIBUTOR_RECEIVED,
          "Distributor",
          duplicateHash,
          "Duplicate record"
        )
    ).to.be.revertedWith("Hash already recorded");
  });

  it("rejects reuse of an AI verification hash", async function () {
    const { ledger, manufacturer, verifier } = await deployFixture();
    await createBatch(ledger, manufacturer);

    const verificationHash = ethers.id("same-image");
    await ledger
      .connect(verifier)
      .logVerification("SG-BATCH-001", verificationHash, Verdict.REAL, 9000, "AI Station", "First scan");

    await expect(
      ledger
        .connect(verifier)
        .logVerification("SG-BATCH-001", verificationHash, Verdict.FAKE, 9500, "AI Station", "Replay scan")
    ).to.be.revertedWith("Hash already recorded");
  });

  it("keeps history append-only through correction events", async function () {
    const { ledger, manufacturer, warehouse } = await deployFixture();
    await createBatch(ledger, manufacturer);

    await ledger
      .connect(warehouse)
      .recordSupplyChainEvent(
        "SG-BATCH-001",
        EventType.WAREHOUSE_RECEIVED,
        "Wrong Warehouse",
        ethers.id("wrong-warehouse"),
        "Original warehouse entry"
      );
    const beforeCorrection = await ledger.getBatchHistory("SG-BATCH-001");

    await ledger
      .connect(warehouse)
      .recordSupplyChainEvent(
        "SG-BATCH-001",
        EventType.CORRECTION,
        "Correct Warehouse",
        ethers.id("warehouse-correction"),
        "Correction: location should be Correct Warehouse"
      );

    const afterCorrection = await ledger.getBatchHistory("SG-BATCH-001");
    expect(afterCorrection.length).to.equal(beforeCorrection.length + 1);
    expect(afterCorrection[1].location).to.equal("Wrong Warehouse");
    expect(afterCorrection[2].eventType).to.equal(EventType.CORRECTION);
    expect(afterCorrection[1].recordId).to.equal(beforeCorrection[1].recordId);
    expect(afterCorrection[2].previousRecordId).to.equal(afterCorrection[1].recordId);
  });

  it("returns complete batch history", async function () {
    const { ledger, manufacturer, warehouse, distributor, verifier } = await deployFixture();
    await createBatch(ledger, manufacturer);
    await ledger
      .connect(warehouse)
      .recordSupplyChainEvent(
        "SG-BATCH-001",
        EventType.WAREHOUSE_RECEIVED,
        "Central Warehouse",
        ethers.id("history-warehouse"),
        "Warehouse received"
      );
    await ledger
      .connect(distributor)
      .recordSupplyChainEvent(
        "SG-BATCH-001",
        EventType.DISTRIBUTOR_RECEIVED,
        "North Distributor",
        ethers.id("history-distributor"),
        "Distributor received"
      );
    await ledger
      .connect(verifier)
      .logVerification(
        "SG-BATCH-001",
        ethers.id("history-fake"),
        Verdict.FAKE,
        9667,
        "AI Station",
        "AI flagged fake"
      );

    const history = await ledger.getBatchHistory("SG-BATCH-001");
    expect(history.map((record) => Number(record.eventType))).to.deep.equal([
      EventType.MANUFACTURED,
      EventType.WAREHOUSE_RECEIVED,
      EventType.DISTRIBUTOR_RECEIVED,
      EventType.FLAGGED_FAKE,
    ]);
  });

  it("blocks unauthorized batch creation and event recording", async function () {
    const { ledger, manufacturer, unauthorized } = await deployFixture();

    await expect(
      ledger
        .connect(unauthorized)
        .createBatch(
          "SG-BATCH-UNAUTH",
          "MED-UNKNOWN",
          "Unknown",
          ethers.id("unauth-create"),
          "Unauthorized create"
        )
    ).to.be.revertedWith("Not authorized manufacturer");

    await createBatch(ledger, manufacturer);
    await expect(
      ledger
        .connect(unauthorized)
        .recordSupplyChainEvent(
          "SG-BATCH-001",
          EventType.WAREHOUSE_RECEIVED,
          "Unknown",
          ethers.id("unauth-event"),
          "Unauthorized event"
        )
    ).to.be.revertedWith("Not authorized participant");
  });
});
