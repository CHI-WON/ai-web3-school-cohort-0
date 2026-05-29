# Proposal 初稿：Agent Service Marketplace

> 赛道：Agentic Commerce / Payment
> 类型：产品（dApp + 协议组合）
> 状态：初稿，待细化

---

## 1. 一句话

一个让 Agent 之间安全交易服务的 marketplace——Agent 发现服务、锁资金进 escrow、服务方交付并提交 proof、验收后自动结算。不需要信任对方，只需要信任链上规则。

---

## 2. 问题定义

### 现在 AI Agent 能做什么？
- 调用 API、搜索网页、生成代码、写报告
- 但只能消费"免费服务"或"预付费 API"

### 卡在哪里？
Agent A 想让 Agent B 帮它完成一个任务（比如写一段代码、跑一次数据分析），愿意付 2 USDC。Agent B 愿意做，但要先拿到钱。

```
A 先付钱 → B 可能不交付
B 先交付 → A 可能不付钱
```

在没有共同第三方的情况下，这个交易做不了。现有方案要么只能做免费任务，要么需要用户手工介入每一步——Agent 失去了"自动委托"的意义。

### 为什么现在这个问题值得解决？
- Agent 能力在爆发（Claude Code、Codex、Hermes），但 Agent 经济基础设施没跟上
- 真实 Agent 需要付费服务：模型推理、数据 API、浏览器环境、代码审计、另一个 Agent 的任务执行
- 没有 Agent-to-Agent 支付，Agent 永远停在 demo 阶段

---

## 3. 目标用户

| 角色 | 描述 |
|------|------|
| **Agent 消费者** | 拥有 Agent 助手的用户/开发者，需要委托任务给其他 Agent 或服务方 |
| **Agent 服务方** | 提供可被 Agent 调用的服务（代码生成、数据分析、链上操作、内容创作），通过 marketplace 接单赚钱 |
| **Evaluator（可选）** | 提供交付质量验证的第三方 Agent 或脚本 |

---

## 4. 核心场景

**场景：Alice 的 Agent 委托 Bob 的 Agent 翻译一篇中文周报**

```
1. Alice Agent 在 marketplace 搜索"中译英翻译"，找到 Bob Agent 的服务
2. Bob Agent 返回 quote：一篇翻译 1 USDC，5 分钟内交付
3. Alice Agent 检查预算（今天的 5 USDC 额度还剩 4 USDC）→ 接受 quote
4. Alice 的 Smart Account 锁定 1 USDC 进 escrow 合约
5. Bob Agent 执行翻译，提交交付：英文版文本 + 原文 hash
6. Evaluator 自动检查：
   - 文本非空？
   - 源语言 ≠ 英文 且 目标文本语言 = 英文？
   - 在 5 分钟内交付？
7. 检查通过 → escrow 释放 1 USDC 给 Bob，生成 receipt
8. Alice 收到翻译结果，预算剩余 3 USDC

恶意场景：
  Bob 提交空白文本 → evaluator 拒绝 → 资金退回 Alice
  Bob 提交原文照抄（中文）→ 语言检测不通过 → 拒绝
  Bob 超时不交 → Alice 触发退款

---

## 5. 关键设计决策

### 5.1 支付闭环（依托 Bridge 六层骨架）

```
Chain-aware Context → Agent 读取 Alice 的链上余额、授权、预算状态
Web3 Tool Use      → 只读：查报价；写入：escrow deposit/release（权限分离）
Agent Workflow     → 状态机：quote_requested → quote_received → funded → delivered → accepted/rejected
Agent Wallet       → Session Key 授权：单次 ≤ 5 USDC | 每天 ≤ 20 USDC | 只调白名单 escrow 合约
Machine Payment    → Quote 签名 + Budget 检查 + Payment Intent（绑定 task ID）
Settlement/Escrow  → 链上 escrow + delivery proof hash + acceptance 规则 + dispute 窗口
```

### 5.2 为什么不用中心化方案？
- 中心化平台 = 共同第三方，但收平台费、可能作恶、单点故障
- 链上 escrow = 规则透明、不可篡改、双方都能验证
- 小额任务用 L2（Arbitrum/Optimism/Base）降低 gas 成本

### 5.3 交付验收怎么保证公平？
- 低风险任务：自动 evaluator（脚本检查格式/字段/时间）
- 中风险任务：AI evaluator 初审 + 1h challenge window
- 高风险任务：AI 初审 + challenge window + 人工/多签仲裁
- 所有 evaluator 结果写入 receipt，成为后续声誉数据

### 5.4 Dispute 机制
- 小额任务（< 1 USDC）：声誉优先，dispute 结果写入链上记录
- 中额任务（1-50 USDC）：服务方预存争议押金，dispute 由多签/仲裁裁决
- 大额任务（> 50 USDC）：必须人工确认 + 独立仲裁

---

## 6. 技术路径

| 层 | 技术选型 | 为什么 |
|----|---------|--------|
| **智能账户** | Safe / ERC-4337 Smart Account | Session Key + Policy + Guard 三层权限 |
| **支付** | USDC（L2） | 稳定、可编程、流动性好 |
| **Escrow** | 链上合约（参考 ERC-8183 思路） | Created → Funded → Delivered → Accepted/Refunded/Disputed |
| **交付证明** | IPFS hash + 链上锚定 | 可验证、不可篡改 |
| **Quote 协议** | 链下签名 quote（参考 x402/MPP 思路） | 轻量、可验证来源、带有效期 |
| **Receipt** | 链上 event + 链下索引 | 机器可读、可作为声誉输入 |
| **发现层** | 链下 registry + 链上声誉锚定 | Agent 能力和信誉可查询 |

---

## 7. 最小可行产品（MVP）

Demo 场景：两个 Agent 完成一次"中译英翻译"交易

MVP 包含：
1. **Escrow 合约**（Solidity）：deposit → deliver(text, originalHash) → accept/reject → release/refund
2. **Quote 生成 + 签名**（链下脚本）
3. **Agent A**：搜索翻译服务 → 检查预算 → deposit → 等待交付 → 自动检查（非空 + 语言检测）→ accept/reject
4. **Agent B**：注册翻译服务 → 响应 quote → 翻译 → 提交交付
5. **最小前端**：用户设置预算、查看交易状态、手动 accept/reject（fallback）

不做/延后：
- 复杂 reputation 系统（MVP 只用交易历史）
- 跨链支付（先用单一 L2）
- 高质量验收（MVP 用语言检测 + 非空，不判断翻译质量）
- 订阅/批量结算

---

## 8. 验证方式

| 验证点 | 方法 |
|--------|------|
| Agent 能否自动完成一次交易？ | Demo：Alice Agent 发起翻译任务 → Bob Agent 交付英文 → 自动验收 → 结算 |
| 恶意服务方能否骗钱？ | 测试：Bob 提交空白文本 → evaluator 拒绝 → 资金退回 Alice |
| 恶意消费者能否白嫖？ | 测试：Alice 拒绝合格翻译 → challenge window 过期 → 资金释放给 Bob |
| 预算控制是否有效？ | 测试：Alice 预算用完 → 新 quote 被 policy 拒绝 |

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Evaluator 误判 | 不靠单一 AI 模型——脚本检查格式 + challenge window + 人工 fallback |
| Gas 成本 > 小额任务价值 | 目标 L2（Base/Optimism），批量结算或预付余额模式 |
| 服务方拖延交付 | Escrow 超时 + Agent 可触发退款 |
| Quote 过期但已付款 | Quote 有效期 + 链上确认时间 buffer |
| 争议仲裁的公正性 | 多签仲裁 + 声誉系统约束 + 争议记录公开 |

---

## 10. 下一步（5/28 - 5/29）

- [ ] 画详细流程图（状态转换 + 各角色交互）
- [ ] 写 escrow 合约草稿（Solidity 伪代码）
- [ ] 明确 MVP scope vs v2 scope
- [ ] 调研现有类似项目（差异化分析）
- [ ] 准备 5/29 例会分享要点

---

## 参考

- Handbook Bridge 章节：Chain-aware Context → Web3 Tool Use → Agent Workflow → Agent Wallet → Machine Payment → Settlement & Escrow
- ERC-8183: Agentic Commerce（标准草案）
- ERC-8004: Trustless Agents（身份+声誉）
- ERC-4337: Account Abstraction
- x402 / MPP: 机器支付协议
- AP2: Agent Payments Protocol
