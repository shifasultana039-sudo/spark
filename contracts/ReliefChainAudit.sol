// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ReliefChainAudit
 * @dev Immutable audit registry for critical AI disaster resource allocations on MST Blockchain.
 * Guarantees cryptographic accountability and tamper-evident decision logs.
 */
contract ReliefChainAudit {
    struct Decision {
        string decisionId;
        bytes32 reportHash;
        uint8 priorityScore;
        uint8 confidenceScore;
        string resourceType;
        uint32 quantity;
        string status;
        address approver;
        uint256 timestamp;
        uint256 blockNumber;
        bool exists;
    }

    address public owner;
    mapping(string => Decision) private _decisions;
    string[] private _decisionIds;

    event DecisionRecorded(
        string indexed decisionId,
        bytes32 indexed reportHash,
        address indexed approver,
        uint8 priorityScore,
        uint8 confidenceScore,
        string resourceType,
        uint32 quantity,
        string status,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "ReliefChainAudit: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Records a newly approved critical emergency decision.
     * Decisions cannot be silently overwritten or modified.
     */
    function recordDecision(
        string calldata decisionId,
        bytes32 reportHash,
        uint8 priorityScore,
        uint8 confidenceScore,
        string calldata resourceType,
        uint32 quantity,
        string calldata status,
        address approver
    ) external {
        require(bytes(decisionId).length > 0, "Invalid decision ID");
        require(!_decisions[decisionId].exists, "Decision ID already recorded and immutable");
        require(priorityScore <= 100, "Invalid priority score");
        require(confidenceScore <= 100, "Invalid confidence score");

        address recordedApprover = approver != address(0) ? approver : msg.sender;

        _decisions[decisionId] = Decision({
            decisionId: decisionId,
            reportHash: reportHash,
            priorityScore: priorityScore,
            confidenceScore: confidenceScore,
            resourceType: resourceType,
            quantity: quantity,
            status: status,
            approver: recordedApprover,
            timestamp: block.timestamp,
            blockNumber: block.number,
            exists: true
        });

        _decisionIds.push(decisionId);

        emit DecisionRecorded(
            decisionId,
            reportHash,
            recordedApprover,
            priorityScore,
            confidenceScore,
            resourceType,
            quantity,
            status,
            block.timestamp
        );
    }

    /**
     * @dev Retrieves on-chain verification data for a recorded decision.
     */
    function getDecision(string calldata decisionId) external view returns (
        string memory id,
        bytes32 reportHash,
        uint8 priorityScore,
        uint8 confidenceScore,
        string memory resourceType,
        uint32 quantity,
        string memory status,
        address approver,
        uint256 timestamp,
        uint256 blockNumber
    ) {
        require(_decisions[decisionId].exists, "Decision not found");
        Decision storage d = _decisions[decisionId];
        return (
            d.decisionId,
            d.reportHash,
            d.priorityScore,
            d.confidenceScore,
            d.resourceType,
            d.quantity,
            d.status,
            d.approver,
            d.timestamp,
            d.blockNumber
        );
    }

    /**
     * @dev Checks if a decision exists and verifies whether an off-chain hash matches the on-chain hash.
     */
    function verifyIntegrity(string calldata decisionId, bytes32 expectedHash) external view returns (bool matches) {
        if (!_decisions[decisionId].exists) {
            return false;
        }
        return _decisions[decisionId].reportHash == expectedHash;
    }

    /**
     * @dev Returns total decisions recorded on-chain.
     */
    function totalDecisions() external view returns (uint256) {
        return _decisionIds.length;
    }
}
