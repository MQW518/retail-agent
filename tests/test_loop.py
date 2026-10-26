"""用假的模型客户端测试主循环：不花 API 费用，也能确定性地复现「调工具 → 再回答」的流程。"""
import copy
import json
from types import SimpleNamespace as NS

from agent.tools import open_store
from agent.loop import MAX_STEPS, new_conversation, run_turn


def tool_call_response(call_id, name, args):
    tc = NS(id=call_id, function=NS(name=name, arguments=json.dumps(args)))
    return NS(choices=[NS(message=NS(content=None, tool_calls=[tc]))])


def text_response(text):
    return NS(choices=[NS(message=NS(content=text, tool_calls=None))])


class FakeClient:
    """按顺序返回预先写好的响应，并记录每次收到的请求。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        # 存快照：messages 之后会被原地追加，真实 SDK 发请求时也是当场序列化
        self.requests.append(copy.deepcopy(kwargs))
        return self.responses.pop(0)


def test_tool_then_answer():
    client = FakeClient([
        tool_call_response("c1", "check_stock", {"product_id": "D002"}),
        text_response("ミネラルウォーターは在庫切れです。"),
    ])
    messages = new_conversation() + [{"role": "user", "content": "水はありますか"}]
    trace = []
    answer = run_turn(client, "fake", open_store(), messages, trace)

    assert answer == "ミネラルウォーターは在庫切れです。"
    assert trace[0][0] == "check_stock"
    # 第二次请求里必须带着 assistant 的 tool_calls 和对应的 tool 结果
    second = client.requests[1]["messages"]
    assert second[-3]["tool_calls"][0]["id"] == "c1"
    assert second[-2] == {"role": "tool", "tool_call_id": "c1", "content": trace[0][2]}
    # 每次请求末尾都附上语言提示，但它不写进对话历史
    assert second[-1]["role"] == "system" and "Japanese" in second[-1]["content"]
    assert all("Reply only in" not in m.get("content", "") for m in messages)
    assert json.loads(trace[0][2])["stock"] == 0


def test_bad_arguments_are_reported_to_model_not_raised():
    client = FakeClient([
        tool_call_response("c1", "check_stock", {}),  # 缺参数
        text_response("どの商品ですか？"),
    ])
    messages = new_conversation() + [{"role": "user", "content": "在庫は？"}]
    trace = []
    run_turn(client, "fake", open_store(), messages, trace)
    assert "error" in json.loads(trace[0][2])


def test_max_steps_guard():
    client = FakeClient([tool_call_response(f"c{i}", "check_stock", {"product_id": "D001"}) for i in range(MAX_STEPS)])
    messages = new_conversation() + [{"role": "user", "content": "loop"}]
    answer = run_turn(client, "fake", open_store(), messages)
    assert "staff" in answer
    assert len(client.requests) == MAX_STEPS


def test_thinking_mode_passes_reasoning_back():
    """思考模式下，assistant 消息必须带着 reasoning_content 回传（否则真实 API 报 400）。"""
    tc = NS(id="c1", function=NS(name="check_stock", arguments='{"product_id": "D001"}'))
    first = NS(choices=[NS(message=NS(content=None, tool_calls=[tc], reasoning_content="需要查库存"))])
    second = NS(choices=[NS(message=NS(content="あります", tool_calls=None, reasoning_content="库存30"))])
    client = FakeClient([first, second])
    messages = new_conversation() + [{"role": "user", "content": "お茶ある？"}]
    run_turn(client, "fake", open_store(), messages, thinking=True)

    assert client.requests[0]["extra_body"] == {"thinking": {"type": "enabled"}}
    assert client.requests[1]["messages"][-3]["reasoning_content"] == "需要查库存"
    assert messages[-1]["reasoning_content"] == "库存30"


def test_thinking_off_does_not_send_reasoning():
    client = FakeClient([text_response("hi")])
    messages = new_conversation() + [{"role": "user", "content": "hello"}]
    run_turn(client, "fake", open_store(), messages)
    assert client.requests[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "reasoning_content" not in messages[-1]


def test_usage_accumulates_and_prices():
    from agent.usage import Usage
    u = Usage()
    u.add(NS(prompt_tokens=1_000_000, prompt_cache_hit_tokens=400_000, completion_tokens=100_000,
             completion_tokens_details=NS(reasoning_tokens=50_000)))
    u.add(None)  # 没有 usage 的响应不计数
    assert u.calls == 1 and u.reasoning_tokens == 50_000
    # 0.4M×0.006 + 0.6M×0.3 + 0.1M×1.2 = 0.0024 + 0.18 + 0.12
    assert abs(u.cost_usd - 0.3024) < 1e-9
