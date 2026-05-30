# Escrow 状态机 + 交互流程

---

## 1. 状态机（合约视角）

```
                    Alice 创建任务
                         │
                         ▼
                   ┌──────────┐
                   │ Created  │
                   └────┬─────┘
                        │ Alice deposit(1 USDC)
                        ▼
                   ┌──────────┐
         超时 ─────│  Funded  │
         退款       └────┬─────┘
                        │ Bob deliver(翻译结果)
                        ▼
                   ┌───────────┐
         超时 ─────│ Delivered │────── 争议 ────┐
         退款       └─────┬─────┘               │
                          │ Alice accept         │
                          ▼                      ▼
                   ┌──────────┐           ┌───────────┐
                   │ Accepted │           │ Disputed  │──→ 人工/多签仲裁
                   └──────────┘           └───────────┘
                    钱 → Bob                  │
                                        ┌─────┴─────┐
                                        ▼           ▼
                                  Released      Refunded
                                   (给 Bob)      (给 Alice)
```

## 2. 交互时序（角色视角）

```
 Alice          Alice          Escrow           Bob            Evaluator
(用户)          Agent          (链上)          Agent           (自动)
  │              │               │               │               │
  │ "翻译这篇"   │               │               │               │
  │─────────────→│               │               │               │
  │              │ search("翻译") │               │               │
  │              │──────────────────────────────→│               │
  │              │               │               │               │
  │              │   quote: 1 USDC, 5min         │               │
  │              │←──────────────────────────────│               │
  │              │               │               │               │
  │              │ createTask()                  │               │
  │              │──────────────→│               │               │
  │              │               │ Created       │               │
  │              │               │               │               │
  │  确认 1 USDC │               │               │               │
  │←─────────────│               │               │               │
  │ OK           │               │               │               │
  │─────────────→│               │               │               │
  │              │ deposit(1 USDC)               │               │
  │              │──────────────→│               │               │
  │              │               │ Funded        │               │
  │              │               │               │               │
  │              │               │     deliver("English text", originalHash)
  │              │               │←──────────────────────────────│
  │              │               │ Delivered     │               │
  │              │               │               │               │
  │              │               │               │ check(非空, 语言=英文)
  │              │               │───────────────────────────────→│
  │              │               │               │    PASS       │
  │              │               │←───────────────────────────────│
  │              │               │               │               │
  │              │ accept()      │               │               │
  │              │──────────────→│               │               │
  │              │               │ Accepted      │               │
  │              │               │───1 USDC─────→│               │
  │              │               │               │               │
  │  翻译结果    │               │               │               │
  │←─────────────│               │               │               │
  │              │               │               │               │
```

## 3. 异常路径

```
场景 A：Bob 超时不交付
─────────────────────────
Funded → 5 min 过期 → Alice 调 refund() → 钱退回 Alice

场景 B：Bob 交空白
─────────────────────────
Funded → Bob deliver(" ") → Delivered → Evaluator 检查 → 非空? NO
→ 验收窗口过期 → Alice 调 refund() → 钱退回 Alice

场景 C：Bob 交中文（没翻译）
─────────────────────────
Funded → Bob deliver("你好世界") → Delivered → Evaluator 检查
→ 语言=英文? NO → 验收窗口过期 → Alice 调 refund()

场景 D：Alice 恶意拒付
─────────────────────────
Funded → Bob deliver(合格翻译) → Delivered → Alice 不调 accept()
→ 验收窗口过期 → Alice 可调 refund() ⚠️
→ 需要 challenge window：Bob 在窗口内调 dispute()
→ 进入 Disputed → 人工仲裁 → 判定合理交付 → 释放给 Bob

## 4. 关键安全点（对应 Security 章）

| 攻击面 | 防护 |
|--------|------|
| 重入攻击 | C-E-I：accept/refund 先改状态再转账 |
| 越权调用 | Access Control：accept/refund 只有 payer；deliver 只有 provider |
| 超时锁死 | deadline + acceptWindow 两层超时，任一到期可退款 |
| 前端跑路 | 合约自托管——Alice 的钱在合约里，不经过 Bob 的前端 |
| 争议无限期 | Dispute 后资金锁定在合约，由仲裁方 multisig 决定方向 |
