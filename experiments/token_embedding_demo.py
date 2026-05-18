"""
Token & Embedding 实操 —— 2026-05-18
让你亲自感受：什么吃 token、token 和字数的巨大差距、以及 embedding 的边界
"""

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / GPT-3.5-turbo

print("=" * 60)
print("实验 1：不同内容类型的 token 消耗对比")
print("=" * 60)

# 场景 A：自然语言
text_cn = "你好，请帮我分析一下这个智能合约的安全性，谢谢。"
tokens_cn = enc.encode(text_cn)

# 场景 B：EVM 地址（长标识符）
text_addr = "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97"
tokens_addr = enc.encode(text_addr)

# 场景 C：JSON
text_json = '{"from":"0x1234...","to":"0x5678...","value":"1000000000000000000","gas":21000,"data":"0xa9059cbb000000000000000000000000"}'
tokens_json = enc.encode(text_json)

# 场景 D：代码
text_code = """function swapExactTokensForTokens(
    uint256 amountIn,
    uint256 amountOutMin,
    address[] calldata path,
    address to,
    uint256 deadline
) external returns (uint256[] memory amounts);"""
tokens_code = enc.encode(text_code)

# 场景 E：中英混排
text_mixed = "这个 Agent 通过 Uniswap V3 Router 执行 swap，slippage 设为 0.5%，deadline 设为 30 minutes。"
tokens_mixed = enc.encode(text_mixed)

print(f"\n{'内容类型':<12} {'字符数':<8} {'Token数':<8} {'Token/字符':<12}")
print("-" * 45)
for label, text, tokens in [
    ("中文自然语言", text_cn, tokens_cn),
    ("EVM 地址", text_addr, tokens_addr),
    ("JSON", text_json, tokens_json),
    ("Solidity 代码", text_code, tokens_code),
    ("中英混排", text_mixed, tokens_mixed),
]:
    print(f"{label:<12} {len(text):<8} {len(tokens):<8} {len(tokens)/len(text):<12.2f}")

print("\n💡 关键观察：")
print("  - EVM 地址 42 个字符 → 消耗 ~30+ token（远超过 1 字符 ≈ 1 token 的直觉）")
print("  - JSON 和代码的 token 密度远高于纯文本")
print("  - 中英混排往往比纯中文更吃 token")


print("\n" + "=" * 60)
print("实验 2：token 分解 —— 看 tokenizer 怎么切")
print("=" * 60)

test = "swapExactTokensForTokens(amountIn, amountOutMin)"
tokens = enc.encode(test)
print(f"\n原文: {test}")
print(f"Token 数: {len(tokens)}")
print("逐个 token:")
for i, t in enumerate(tokens):
    print(f"  [{i:2d}] id={t:<6d} → '{enc.decode([t])}'")

print("\n💡 看：'swap'、'Exact'、'Tokens'、'For'、'Tokens' 被切成多个 token")
print("   驼峰命名对 tokenizer 不友好 —— 每个单词片段都是独立 token")


print("\n" + "=" * 60)
print("实验 3：Embedding 的边界（概念演示）")
print("=" * 60)

print("""
场景：用户问 "这个合约安全吗？" → 向量库检索到相似文档

相似度 0.94 的文档：  "该合约已通过 CertiK 审计，未发现高危漏洞"
相似度 0.92 的文档：  "该合约疑似存在重入攻击，请勿交互"
相似度 0.91 的文档：  "今天天气真好，适合写代码"

问题：
  - 0.94 和 0.92 的文档结论完全相反，你信哪个？
  - 0.91 虽然相似度不低，但和安全性完全无关

结论：
  ✅ Embedding 帮你从海量文档中找到"话题相关"的内容
  ❌ Embedding 不能帮你判断"结论是否正确"
  🔑 向量相似 ≠ 事实正确 ≠ 信源可靠
  🔑 必须加：来源校验、时间戳、审计状态、规则引擎
""")
