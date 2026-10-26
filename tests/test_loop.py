"""用假的模型客户端测试主循环：不花 API 费用，也能确定性地复现「调工具 → 再回答」的流程。"""
import copy
import json
from types import SimpleNamespace as NS

from agent.db import connect
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
    answer = run_turn(client, "fake", connect(), messages, trace)

    assert answer == "ミネラルウォーターは在庫切れです。"
    assert trace[0][0] == "check_stock"
    # 第二次请求里必须带着 assistant 的 tool_calls 和对应的 tool 结果
    second = client.requests[1]["messages"]
    assert second[-2]["tool_calls"][0]["id"] == "c1"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": trace[0][2]}
    assert json.loads(trace[0][2])["stock"] == 0


def test_bad_arguments_are_reported_to_model_not_raised():
    client = FakeClient([
        tool_call_response("c1", "check_stock", {}),  # 缺参数
        text_response("どの商品ですか？"),
    ])
    messages = new_conversation() + [{"role": "user", "content": "在庫は？"}]
    trace = []
    run_turn(client, "fake", connect(), messages, trace)
    assert "error" in json.loads(trace[0][2])


def test_max_steps_guard():
    client = FakeClient([tool_call_response(f"c{i}", "check_stock", {"product_id": "D001"}) for i in range(MAX_STEPS)])
    messages = new_conversation() + [{"role": "user", "content": "loop"}]
    answer = run_turn(client, "fake", connect(), messages)
    assert "staff" in answer
    assert len(client.requests) == MAX_STEPS
