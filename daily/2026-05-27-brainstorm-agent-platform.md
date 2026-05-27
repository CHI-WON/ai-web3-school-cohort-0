# 脑暴存档：Agent-Native Platform 方向

> 2026-05-27 21:22 — 原始讨论，待后续深入

## 核心直觉

未来人人有 agent 助手（Jarvis 式），需要搭建专门给 agent 使用的 platform（类比：给人做 app/web，给 agent 做 dapp）。设想搭建在区块链上的 dapp，比如 agent 订阅购买服务。

## Agent 的犀利指正

1. **混淆了 Agent Platform（执行环境/能力发现）和 Agent Commerce（经济交换/定价结算）**
2. **Jarvis 隐喻在误导** — 单用户高信任 vs 多 agent 低信任开放网络
3. **"区块链 dapp"只解决了结算层** — 发现、身份、验证、争议、仲裁都没想

## 展开的三个方向

### A. Agent Service Marketplace
agent 的 AWS：发现 → 协商 → escrow → 执行 → proof-of-delivery → 结算/争议

### B. Agent Capability Registry + Discovery
MCP/A2A 上加公开能力声明 + 链上信誉

### C. Agent-Native Payment Channel
agent 间微支付底层通道（类似 Lightning 但为 API 调用优化）

## 核心问题（待回答）

两个互不信任的 agent，在没有共同第三方的情况下，怎么完成"你帮我做一件事，我付你钱"的交易？现在为什么做不了？我的方案补了哪一块？

## 关联

- Week 2 Module B: Payment / Commerce / Settlement
- Week 2 Module C: Identity / Reputation / Capability / Interoperability
- 报名 track: verifiable_agent_identity, agent_payment_commerce
