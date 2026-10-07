// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SupplyGuardLedger {
    enum SupplyChainEventType {
        MANUFACTURED,
        PACKAGED,
        QUALITY_CHECK,
        WAREHOUSE_RECEIVED,
        DISTRIBUTOR_RECEIVED,
        RETAILER_RECEIVED,
        VERIFIED,
        FLAGGED_FAKE,
        CORRECTION
    }

    enum Verdict {
        NONE,
        REAL,
        FAKE
    }

    struct Batch {
        string batchId;
        string productId;
        address manufacturer;
        uint256 createdAt;
        bool exists;
    }

    struct LedgerRecord {
        bytes32 recordId;
        string batchId;
        string productId;
        SupplyChainEventType eventType;
        address actor;
        uint256 timestamp;
        string location;
        bytes32 dataHash;
        Verdict verdict;
        uint16 confidenceBps;
        bytes32 previousRecordId;
        string notes;
    }

    address public owner;

    mapping(address => bool) public authorizedManufacturers;
    mapping(address => bool) public authorizedParticipants;
    mapping(string => Batch) private batches;
    mapping(string => LedgerRecord[]) private batchHistory;
    mapping(bytes32 => bool) public usedDataHashes;

    event ManufacturerAuthorizationChanged(address indexed account, bool authorized);
    event ParticipantAuthorizationChanged(address indexed account, bool authorized);
    event BatchCreated(
        string indexed batchId,
        string productId,
        address indexed manufacturer,
        uint256 timestamp
    );
    event SupplyChainEventRecorded(
        string indexed batchId,
        bytes32 indexed recordId,
        SupplyChainEventType eventType,
        address indexed actor,
        uint256 timestamp,
        bytes32 dataHash
    );
    event VerificationLogged(
        string indexed batchId,
        bytes32 indexed recordId,
        Verdict verdict,
        uint16 confidenceBps,
        bytes32 indexed dataHash
    );
    event FakeMedicineFlagged(
        string indexed batchId,
        bytes32 indexed recordId,
        uint16 confidenceBps,
        bytes32 indexed dataHash
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyManufacturer() {
        require(authorizedManufacturers[msg.sender], "Not authorized manufacturer");
        _;
    }

    modifier onlyParticipant() {
        require(authorizedParticipants[msg.sender], "Not authorized participant");
        _;
    }

    modifier batchExists(string calldata batchId) {
        require(batches[batchId].exists, "Batch does not exist");
        _;
    }

    constructor() {
        owner = msg.sender;
        authorizedManufacturers[msg.sender] = true;
        authorizedParticipants[msg.sender] = true;
        emit ManufacturerAuthorizationChanged(msg.sender, true);
        emit ParticipantAuthorizationChanged(msg.sender, true);
    }

    function setManufacturerAuthorization(address account, bool authorized) external onlyOwner {
        require(account != address(0), "Invalid account");
        authorizedManufacturers[account] = authorized;
        if (authorized) {
            authorizedParticipants[account] = true;
            emit ParticipantAuthorizationChanged(account, true);
        }
        emit ManufacturerAuthorizationChanged(account, authorized);
    }

    function setParticipantAuthorization(address account, bool authorized) external onlyOwner {
        require(account != address(0), "Invalid account");
        authorizedParticipants[account] = authorized;
        emit ParticipantAuthorizationChanged(account, authorized);
    }

    function createBatch(
        string calldata batchId,
        string calldata productId,
        string calldata location,
        bytes32 dataHash,
        string calldata notes
    ) external onlyManufacturer {
        require(bytes(batchId).length > 0, "Batch ID required");
        require(bytes(productId).length > 0, "Product ID required");
        require(!batches[batchId].exists, "Batch already exists");
        _validateNewHash(dataHash);

        batches[batchId] = Batch({
            batchId: batchId,
            productId: productId,
            manufacturer: msg.sender,
            createdAt: block.timestamp,
            exists: true
        });

        emit BatchCreated(batchId, productId, msg.sender, block.timestamp);
        _appendRecord(
            batchId,
            productId,
            SupplyChainEventType.MANUFACTURED,
            location,
            dataHash,
            Verdict.NONE,
            0,
            notes
        );
    }

    function recordSupplyChainEvent(
        string calldata batchId,
        SupplyChainEventType eventType,
        string calldata location,
        bytes32 dataHash,
        string calldata notes
    ) external onlyParticipant batchExists(batchId) {
        require(eventType != SupplyChainEventType.MANUFACTURED, "Use createBatch");
        require(eventType != SupplyChainEventType.VERIFIED, "Use logVerification");
        require(eventType != SupplyChainEventType.FLAGGED_FAKE, "Use logVerification");
        _validateNewHash(dataHash);

        _appendRecord(
            batchId,
            batches[batchId].productId,
            eventType,
            location,
            dataHash,
            Verdict.NONE,
            0,
            notes
        );
    }

    function logVerification(
        string calldata batchId,
        bytes32 verificationHash,
        Verdict verdict,
        uint16 confidenceBps,
        string calldata location,
        string calldata notes
    ) external onlyParticipant batchExists(batchId) {
        require(verdict == Verdict.REAL || verdict == Verdict.FAKE, "Invalid verdict");
        require(confidenceBps <= 10000, "Invalid confidence");
        _validateNewHash(verificationHash);

        SupplyChainEventType eventType = verdict == Verdict.FAKE
            ? SupplyChainEventType.FLAGGED_FAKE
            : SupplyChainEventType.VERIFIED;

        bytes32 recordId = _appendRecord(
            batchId,
            batches[batchId].productId,
            eventType,
            location,
            verificationHash,
            verdict,
            confidenceBps,
            notes
        );

        emit VerificationLogged(batchId, recordId, verdict, confidenceBps, verificationHash);
        if (verdict == Verdict.FAKE) {
            emit FakeMedicineFlagged(batchId, recordId, confidenceBps, verificationHash);
        }
    }

    function getBatch(string calldata batchId) external view returns (Batch memory) {
        require(batches[batchId].exists, "Batch does not exist");
        return batches[batchId];
    }

    function getBatchHistory(string calldata batchId) external view returns (LedgerRecord[] memory) {
        require(batches[batchId].exists, "Batch does not exist");
        return batchHistory[batchId];
    }

    function getBatchHistoryLength(string calldata batchId) external view returns (uint256) {
        require(batches[batchId].exists, "Batch does not exist");
        return batchHistory[batchId].length;
    }

    function getLatestRecord(string calldata batchId) external view returns (LedgerRecord memory) {
        require(batches[batchId].exists, "Batch does not exist");
        uint256 length = batchHistory[batchId].length;
        require(length > 0, "No records");
        return batchHistory[batchId][length - 1];
    }

    function _appendRecord(
        string calldata batchId,
        string memory productId,
        SupplyChainEventType eventType,
        string calldata location,
        bytes32 dataHash,
        Verdict verdict,
        uint16 confidenceBps,
        string calldata notes
    ) private returns (bytes32) {
        LedgerRecord[] storage history = batchHistory[batchId];
        bytes32 previousRecordId = history.length == 0
            ? bytes32(0)
            : history[history.length - 1].recordId;
        bytes32 recordId = keccak256(
            abi.encodePacked(
                batchId,
                productId,
                eventType,
                msg.sender,
                block.timestamp,
                dataHash,
                previousRecordId,
                history.length
            )
        );

        usedDataHashes[dataHash] = true;
        history.push(
            LedgerRecord({
                recordId: recordId,
                batchId: batchId,
                productId: productId,
                eventType: eventType,
                actor: msg.sender,
                timestamp: block.timestamp,
                location: location,
                dataHash: dataHash,
                verdict: verdict,
                confidenceBps: confidenceBps,
                previousRecordId: previousRecordId,
                notes: notes
            })
        );

        emit SupplyChainEventRecorded(
            batchId,
            recordId,
            eventType,
            msg.sender,
            block.timestamp,
            dataHash
        );
        return recordId;
    }

    function _validateNewHash(bytes32 dataHash) private view {
        require(dataHash != bytes32(0), "Hash required");
        require(!usedDataHashes[dataHash], "Hash already recorded");
    }
}

