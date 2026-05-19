"""
交易风险摘要 Prompt — 最小实践
Handbook: https://aiweb3.school/zh/handbook/ai-basics/prompt/

设计思路：
  - Instruction 四段：任务目标 / 可用输入 / 禁止行为 / 输出格式
  - Structured Output：JSON schema，下游代码可直接校验
"""

PROMPT = """你是交易风险分析助手。你的职责是分析待签名的链上交易，标记潜在风险，但绝不替用户做决定。

## 可用输入
你会收到以下信息（如有缺失，在 uncertainties 中标注）：
- target_address: 交易目标合约地址
- function_name: 调用的函数名
- parameters: 函数参数
- asset_changes: 预期资产变化（转入/转出）
- simulation_result: 模拟交易结果（success/failure，含错误信息）
- user_intent: 用户用自然语言描述的操作意图

## 禁止行为
- 不要替用户确认交易
- 不要编造输入中不存在的信息
- 不要把不确定的事标记为安全
- 不要建议用户忽略 simulation 失败

## 输出格式
严格输出以下 JSON，不含任何额外文字：

{
  "summary": "一句话摘要",
  "asset_changes": ["资产A: +1.5 ETH", "资产B: -2000 USDC"],
  "permissions_changed": ["approve USDC to 0xDEF..."],
  "risk_level": "low" | "medium" | "high",
  "requires_human_approval": true | false,
  "uncertainties": ["不确定项1", "不确定项2"],
  "recommended_user_checks": ["建议用户做的事"]
}
"""

# ─── 3 组测试用例 ───────────────────────────────────────────

test_cases = [
    {
        "name": "测试 1: 普通转账 — 应标记为 low risk",
        "input": {
            "target_address": "0xAlice",
            "function_name": "transfer",
            "parameters": {"to": "0xBob", "amount": "0.5 ETH"},
            "asset_changes": ["-0.5 ETH (from sender)"],
            "simulation_result": "success",
            "user_intent": "给 Bob 转 0.5 ETH"
        },
        "expected": {
            "risk_level": "low",
            "requires_human_approval": False,
            "checks": [
                "simulation 成功",
                "目标地址 0xAlice 是已知合约/EOA",
                "asset_changes 与用户意图匹配（0.5 ETH）",
                "没有权限变更（transfer 不涉及 approve）"
            ]
        }
    },
    {
        "name": "测试 2: 无限授权 — 应标记为 high risk",
        "input": {
            "target_address": "0xUSDC",
            "function_name": "approve",
            "parameters": {"spender": "0xUnknownDEX", "amount": "115792089237316195423570985008687907853269984665640564039457584007913129639935"},
            "asset_changes": [],
            "simulation_result": "success",
            "user_intent": "授权 USDC 给 DEX 用于交易"
        },
        "expected": {
            "risk_level": "high",
            "requires_human_approval": True,
            "checks": [
                "amount 是 uint256 max（= 无限授权）",
                "spender 0xUnknownDEX 不在已知合约白名单",
                "无限授权意味着该合约可以随时转走所有 USDC",
                "应建议用户改用精确金额授权"
            ]
        }
    },
    {
        "name": "测试 3: 目标地址与用户意图不匹配 — 应标记为 high risk",
        "input": {
            "target_address": "0xScamToken",
            "function_name": "swapExactTokensForTokens",
            "parameters": {"amountIn": "1000 USDC", "path": ["0xUSDC", "0xScamToken"]},
            "asset_changes": ["-1000 USDC", "+999999 SCAM"],
            "simulation_result": "success",
            "user_intent": "用 1000 USDC 换 UNI"
        },
        "expected": {
            "risk_level": "high",
            "requires_human_approval": True,
            "checks": [
                "用户说想换 UNI，但输出代币是 SCAM",
                "输出数量 999,999 是典型的蜜罐代币特征",
                "目标地址 0xScamToken 不在已知 DEX 列表",
                "simulation success 不代表安全（蜜罐代币交易本身可成功）"
            ]
        }
    }
]

# ─── 验证逻辑（模拟下游 code 层校验）─────────────────────

def validate_output(output: dict):
    """模拟 code 层对模型输出的 schema 校验和 guard 检查"""
    errors = []
    required = ["summary", "asset_changes", "permissions_changed",
                "risk_level", "requires_human_approval", "uncertainties",
                "recommended_user_checks"]
    for field in required:
        if field not in output:
            errors.append(f"缺少字段: {field}")

    if output.get("risk_level") not in ("low", "medium", "high"):
        errors.append(f"risk_level 非法值: {output.get('risk_level')}")
    if not isinstance(output.get("requires_human_approval"), bool):
        errors.append("requires_human_approval 必须是 boolean")
    if not isinstance(output.get("uncertainties"), list):
        errors.append("uncertainties 必须是数组")

    # Guard: high risk 强制 human approval
    if output.get("risk_level") == "high" and not output.get("requires_human_approval"):
        errors.append("GUARD: risk_level=high 但 requires_human_approval=false")

    return errors


# ─── 主程序 ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("交易风险摘要 Prompt — 最小实践")
    print("=" * 56)
    print()
    print("📋 PROMPT 模板:")
    print("-" * 40)
    print(PROMPT)
    print("-" * 40)
    print()

    for i, tc in enumerate(test_cases, 1):
        print(f"🧪 {tc['name']}")
        print(f"   输入摘要: {tc['input']['function_name']} → {tc['input']['user_intent']}")
        print(f"   期望 risk_level: {tc['expected']['risk_level']}")
        print(f"   期望 human_approval: {tc['expected']['requires_human_approval']}")
        print(f"   核心检查点:")
        for check in tc['expected']['checks']:
            print(f"     ✓ {check}")
        print()

    print("=" * 56)
    print("💡 核心 insight")
    print("=" * 56)
    print("1. Prompt 定义任务和输出 schema（软约束）")
    print("2. 下游 code 校验 schema + enforce guard 规则（硬约束）")
    print("3. Prompt + Structured Output + Guard 三者配合，")
    print("   才能在工程中安全使用 LLM 做交易分析")
    print()
    print("▶  运行方式：把 prompt + 3 个测试用例的 input 喂给 LLM API，")
    print("   然后对输出跑 validate_output() 检查")
