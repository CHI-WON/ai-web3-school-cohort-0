// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * Agent Service Marketplace — Escrow 合约
 * 
 * 场景：Alice Agent 花 1 USDC 委托 Bob Agent 翻译一篇文档
 * 
 * 安全设计（来自 Security 章）：
 *   - Checks-Effects-Interactions：所有外部调用前先改状态
 *   - Access Control：release/refund 只能由付款方或超时触发
 *   - Reentrancy Guard：release/refund 使用 C-E-I 模式
 * 
 * 权限设计（来自 Account Abstraction 章）：
 *   - Session Key：Alice 的 Smart Account 通过 session key 调用 deposit/release
 *   - 不在合约层限制额度，由 AA 的 policy 层管理
 */

contract AgentEscrow {
    // ============ 状态机（Settlement & Escrow 章） ============
    enum State { Created, Funded, Delivered, Accepted, Refunded, Disputed }

    struct Task {
        address payer;          // 付款方（Alice 的 Smart Account）
        address provider;       // 服务方（Bob）
        uint256 amount;         // 锁定金额
        bytes32 quoteId;        // 关联的 quote ID（Machine Payment 章）
        string deliveryProof;   // 交付证明（IPFS hash / 文本 hash）
        string originalHash;    // 原文 hash（用于验证翻译对应关系）
        uint256 deadline;       // 交付截止时间
        uint256 acceptWindow;   // 验收窗口（到期前）
        State state;
    }

    mapping(bytes32 => Task) public tasks;

    // ============ Events（Indexing 章：链上日志 = 可索引收据） ============
    event TaskCreated(bytes32 indexed taskId, address payer, address provider, uint256 amount);
    event TaskFunded(bytes32 indexed taskId);
    event TaskDelivered(bytes32 indexed taskId, string deliveryProof);
    event TaskAccepted(bytes32 indexed taskId);
    event TaskRefunded(bytes32 indexed taskId);
    event TaskDisputed(bytes32 indexed taskId, string reason);

    // ============ 核心函数 ============

    /// 1. 创建任务（Alice 发起）
    function createTask(
        bytes32 taskId,
        address provider,
        bytes32 quoteId,
        string calldata originalHash,
        uint256 deliveryMinutes,
        uint256 acceptMinutes
    ) external {
        require(tasks[taskId].payer == address(0), "Task exists");
        require(provider != address(0), "Invalid provider");
        // 引用 Quote 确保可追溯（Machine Payment 章）
        require(quoteId != bytes32(0), "Quote required");

        tasks[taskId] = Task({
            payer: msg.sender,
            provider: provider,
            amount: 0,
            quoteId: quoteId,
            deliveryProof: "",
            originalHash: originalHash,
            deadline: block.timestamp + deliveryMinutes * 1 minutes,
            acceptWindow: block.timestamp + (deliveryMinutes + acceptMinutes) * 1 minutes,
            state: State.Created
        });

        emit TaskCreated(taskId, msg.sender, provider, 0);
    }

    /// 2. 存入资金（Alice 锁钱进 escrow）
    function deposit(bytes32 taskId) external payable {
        Task storage t = tasks[taskId];
        require(msg.sender == t.payer, "Only payer");
        require(t.state == State.Created, "Not in Created");
        require(msg.value > 0, "Amount must be > 0");

        t.amount = msg.value;
        t.state = State.Funded;

        emit TaskFunded(taskId);
    }

    /// 3. 服务方提交交付（Bob 提交翻译结果）
    function deliver(bytes32 taskId, string calldata proof) external {
        Task storage t = tasks[taskId];
        require(msg.sender == t.provider, "Only provider");
        require(t.state == State.Funded, "Not in Funded");
        require(block.timestamp <= t.deadline, "Deadline passed");
        require(bytes(proof).length > 0, "Empty proof");

        // C-E-I：先改状态
        t.deliveryProof = proof;
        t.state = State.Delivered;

        emit TaskDelivered(taskId, proof);
    }

    /// 4. 验收通过，释放付款
    /// ⚠️ Checks-Effects-Interactions：先改状态，再转账（防重入）
    function accept(bytes32 taskId) external {
        Task storage t = tasks[taskId];
        require(msg.sender == t.payer, "Only payer");
        require(t.state == State.Delivered, "Not in Delivered");

        // Check
        uint256 amount = t.amount;
        address payable provider = payable(t.provider);

        // Effects（先改状态！）
        t.state = State.Accepted;

        // Interactions（最后转账）
        (bool ok, ) = provider.call{value: amount}("");
        require(ok, "Transfer failed");

        emit TaskAccepted(taskId);
    }

    /// 5. 退款（交付超时 或 验收失败）
    /// ⚠️ 同样使用 C-E-I
    function refund(bytes32 taskId) external {
        Task storage t = tasks[taskId];
        require(msg.sender == t.payer, "Only payer");

        // 两种退款触发条件
        bool expired = block.timestamp > t.deadline && t.state == State.Funded;
        bool rejected = t.state == State.Delivered && block.timestamp > t.acceptWindow;
        require(expired || rejected, "Cannot refund yet");

        // Check
        uint256 amount = t.amount;
        address payable payer = payable(t.payer);

        // Effects
        t.state = State.Refunded;

        // Interactions
        (bool ok, ) = payer.call{value: amount}("");
        require(ok, "Transfer failed");

        emit TaskRefunded(taskId);
    }

    /// 6. 争议（双方均可发起）
    function dispute(bytes32 taskId, string calldata reason) external {
        Task storage t = tasks[taskId];
        require(
            msg.sender == t.payer || msg.sender == t.provider,
            "Only payer or provider"
        );
        require(
            t.state == State.Delivered || t.state == State.Funded,
            "Cannot dispute in current state"
        );

        t.state = State.Disputed;

        emit TaskDisputed(taskId, reason);
    }

    // ============ View 函数（Chain-aware Context 章：Agent 读取链上状态） ============

    function getTask(bytes32 taskId) external view returns (Task memory) {
        return tasks[taskId];
    }
}
