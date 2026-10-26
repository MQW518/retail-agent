"""token 用量与费用统计。

价格来自 DeepSeek 官方价格页（2026-10-26 查询），deepseek-flash，每 100 万 token，美元，按**高峰时段**计算：
非高峰时段是半价，所以这里算出的是费用上限。
"""
from dataclasses import dataclass

PRICE_PER_M = {"cache_hit": 0.006, "cache_miss": 0.3, "output": 1.2}


@dataclass
class Usage:
    calls: int = 0              # 调用模型的次数
    prompt_tokens: int = 0
    cache_hit_tokens: int = 0   # 输入里命中缓存的部分（DeepSeek 特有字段）
    completion_tokens: int = 0  # 输出（含思考模式的推理 token）
    reasoning_tokens: int = 0

    def add(self, api_usage) -> None:
        if api_usage is None:
            return
        self.calls += 1
        self.prompt_tokens += api_usage.prompt_tokens or 0
        self.cache_hit_tokens += getattr(api_usage, "prompt_cache_hit_tokens", 0) or 0
        self.completion_tokens += api_usage.completion_tokens or 0
        details = getattr(api_usage, "completion_tokens_details", None)
        self.reasoning_tokens += (getattr(details, "reasoning_tokens", 0) or 0) if details else 0

    @property
    def cost_usd(self) -> float:
        miss = self.prompt_tokens - self.cache_hit_tokens
        return (self.cache_hit_tokens * PRICE_PER_M["cache_hit"] + miss * PRICE_PER_M["cache_miss"]
                + self.completion_tokens * PRICE_PER_M["output"]) / 1_000_000

    def as_dict(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt_tokens, "cache_hit_tokens": self.cache_hit_tokens,
                "completion_tokens": self.completion_tokens, "reasoning_tokens": self.reasoning_tokens,
                "cost_usd": round(self.cost_usd, 6)}
