# Proposal：Agent Service Marketplace

> 赛道：Agentic Commerce / Payment
> 类型：产品（Smart Contract + Agent 交互协议）
> 状态：最终稿
> 附件：`escrow-contract.sol`（合约伪代码） / `escrow-flowchart.md`（状态机 + 时序图）

---

## 1. 一句话

一个让 Agent 之间安全交易服务的 marketplace——Agent 发现服务 → 锁资金进 escrow → 服务方交付 proof → 自动验收 → 结算。不需要信任对方，只需要信任链上规则。

---

## 2. 问题定义

### 现在 AI Agent 能做什么？
- 调用 API、搜索网页、生成代码、写报告
- 但只能消费"免费服务"或"预付费 API"

### 卡在哪里？
Agent A 想让 Agent B 帮它完成任务（翻译、格式转换、代码审查），愿意付费。Agent B 愿意做，但要先拿到钱。

```
A 先付钱 → B 可能不交付
B 先交付 → A 可能不付钱
```

没有共同第三方时，这个交易做不了。现有方案要么只做免费任务，要么需要用户手工介入每一步——Agent 失去"自动委托"的意义。

### 为什么现在值得做？
- Agent 能力爆发（Claude Code、Codex、Hermes），但 Agent 经济基础设施没跟上
- 真实 Agent 需要付费服务：模型推理、数据 API、浏览器环境、另一个 Agent 的任务执行
- 没有 Agent-to-Agent 安全支付，Agent 永远停在 demo

---

## 3. 目标用户

| 角色 | 描述 |
|------|------|
| Agent 消费者 | 拥有 Agent 助手的用户/开发者，委托任务给其他 Agent 或服务方 |
| Agent 服务方 | 提供可被 Agent 调用的服务，通过 marketplace 接单赚钱 |
| Evaluator | 可选——提供交付验证的第三方脚本或 Agent |

---

## 4. 核心场景

**Alice Agent 花 1 USDC 委托 Bob Agent 翻译一篇中文周报**

```
1. Alice Agent 在 marketplace 搜索"中译英翻译"，找到 Bob Agent
2. Bob Agent 返回签名的 quote：一篇 1 USDC，5 分钟交付
3. Alice Agent 检查预算（剩余 4/5 USDC）→ 接受 quote → createTask()
4. Alice 的 Smart Account deposit 1 USDC 进 escrow 合约
5. Bob Agent 翻译 → deliver(英文文本, 原文hash)
6. Evaluator 自动检查：
   - 文本非空 ✓
   - 语言检测 = 英文 ✓
   - 5 分钟内交付 ✓
7. 通过 → accept() → 1 USDC 释放给 Bob → 链上 receipt
8. Alice 收到翻译，预算剩余 3 USDC
```

**三个恶意场景与防护：**

| 攻击 | 检测 | 结果 |
|------|------|------|
| Bob 交空白文本 | evaluator：文本为空 | 资金退回 Alice |
| Bob 交原文照抄 | evaluator：语言 ≠ 英文 | 资金退回 Alice |
| Bob 超时不交 | deadline 过期 | Alice 调 refund() 退款 |
| Alice 恶意拒付 | Bob 在验收窗口内调 dispute() | 进入仲裁 |

---

## 5. 技术架构

### 5.1 支付闭环（Bridge 六层骨架）

```
Chain-aware Context  → Agent 读取 Alice 的余额、授权、预算状态
Web3 Tool Use        → 只读：查报价、语言检测 │ 写入：deposit/accept/refund
Agent Workflow       → 状态机：Created→Funded→Delivered→Accepted/Refunded/Disputed
Agent Wallet         → Session Key 授权：单次 ≤5 USDC │ 每天 ≤20 USDC │ 白名单合约
Machine Payment      → Quote 签名 + Budget 检查 + Payment Intent（绑定 taskId）
Settlement/Escrow    → 链上 escrow + delivery proof + accept 规则 + dispute 窗口
```

### 5.2 Escrow 合约核心设计（附件：`escrow-contract.sol`）

```
六个函数 → 完整状态机：

  createTask()       payer 创建任务，绑定 quoteId + 原文 hash + 时间窗口
  deposit()          payer 锁定资金 → Funded
  deliver(proof)     provider 提交交付 → Delivered
  accept()           payer 验收通过 → 释放资金给 provider
  refund()           超时或验收失败 → 退还给 payer
  dispute(reason)    双方可发起 → 仲裁决定方向
```

**安全设计（Web3 Security 章直接映射）：**

| 攻击面 | 防护 |
|--------|------|
| 重入攻击 | Checks-Effects-Interactions：accept/refund 先改状态再转账 |
| 越权调用 | Access Control：accept/refund 只有 payer；deliver 只有 provider |
| 超时锁死 | deadline（交付截止）+ acceptWindow（验收窗口），任一到期可退款 |
| 资金托管 | 资金在合约里，不经过服务方前端，跑路也拿不到钱 |

### 5.3 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 智能账户 | Safe / ERC-4337 Smart Account | Session Key + Policy + Guard 三层权限 |
| 支付 | USDC（L2：Base/Optimism） | 稳定、可编程、gas 低 |
| Escrow | 链上合约（参考 ERC-8183） | 状态机 + C-E-I + event 日志 |
| 交付证明 | 文本 hash + 原文 hash 对照 | 轻量、可验证 |
| Quote | 链下签名 quote（参考 x402/MPP） | 可验证来源、带有效期 |
| Receipt | 链上 event + 链下索引 | 机器可读、声誉系统输入 |
| 发现层 | 链下 registry + 链上信誉锚定 | 可查询、不可篡改 |

### 5.4 为什么不用中心化方案？

- 中心化 = 共同第三方，但抽成、可能作恶、单点故障
- 链上 escrow = 规则透明、双方可验证、不依赖平台信用
- 小额任务走 L2，gas 成本可控

---

## 6. MVP 范围

**Demo：两个 Agent 完成一次"中译英翻译"交易**

包含：
1. Escrow 合约（Solidity）：`createTask → deposit → deliver → accept/refund/dispute`
2. Quote 生成 + 签名（链下脚本）
3. Agent A：搜索翻译 → 检查预算 → deposit → 自动验收（非空 + 语言检测）→ accept
4. Agent B：注册服务 → 响应 quote → 翻译 → deliver
5. 最小前端：用户设预算、看状态、手动 accept（fallback）

延后（v2）：
- 复杂 reputation 系统（MVP 只用交易历史）
- 跨链支付（MVP 单一 L2）
- 翻译质量评估（MVP 用语言检测 + 非空，不判质量）
- 订阅 / 批量结算

---

## 7. 验证计划

| 验证点 | 方法 |
|--------|------|
| Agent 能否自动完成交易？ | Demo：Alice 发起翻译 → Bob 交付 → 自动验收 → 结算 |
| 恶意服务方能骗钱吗？ | 测试：Bob 交空白 → evaluator 拒绝 → 退款 |
| 恶意消费者能白嫖吗？ | 测试：Alice 拒付合理交付 → Bob dispute → 仲裁释放 |
| 预算控制有效吗？ | 测试：Alice 预算耗尽 → 新 quote 被 policy 拒绝 |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Evaluator 误判 | 不靠单一 AI——脚本检查格式 + challenge window + 人工 fallback |
| Gas 成本 > 任务价值 | 目标 L2（Base/Optimism），v2 探索批量结算 |
| 拖延交付 | deadline 超时 → payer 可触发 refund |
| Quote 过期 | 签名 quote 带有效期 + 链上确认时间 buffer |
| 争议仲裁公正性 | 多签仲裁 + 争议记录公开 → 声誉系统约束 |

---

## 9. 差异化

现有 agent 委托方案（如 CrewAI、AutoGen 的多 agent 协作）解决的是"怎么分配任务"，但支付环节仍然是免费或人工。本方案补的是 **Agent 之间的经济层**——把"我帮你做一件事，你付我钱"变成链上可验证、可自动执行的流程。

核心差异：
- 不是另一个 agent 框架，是 agent 的 **支付基础设施**
- 不是中心化撮合平台，是 **链上规则替代信任**
- 不要求 agent 同属一个系统，任意 agent 只要遵守 quote + escrow 协议就能交易

---

## 10. 附件清单

| 文件 | 说明 |
|------|------|
| `escrow-contract.sol` | Escrow 合约伪代码（6 函数 + 状态机 + C-E-I 安全模式） |
| `escrow-flowchart.md` | 状态转换图 + 交互时序图 + 4 个异常路径 |

---

## 参考

- Handbook Bridge 六章：Chain-aware Context → Web3 Tool Use → Agent Workflow → Agent Wallet → Machine Payment → Settlement & Escrow
- Handbook Web3 基础：Smart Contract / Security（C-E-I + Access Control）/ Account Abstraction（Session Key）
- ERC-8183: Agentic Commerce / ERC-8004: Trustless Agents / ERC-4337: Account Abstraction
- x402 / MPP: 机器支付协议
