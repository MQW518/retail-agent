"""接口测试：用假的模型客户端，不调用真实 API。"""
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

from server import create_app
from test_loop import FakeClient, text_response, tool_call_response


def with_usage(resp, prompt=100, completion=20):
    resp.usage = NS(prompt_tokens=prompt, prompt_cache_hit_tokens=0, completion_tokens=completion,
                    completion_tokens_details=None)
    return resp


def make(responses):
    fake = FakeClient(responses)
    return TestClient(create_app(client=fake, model="fake-model")), fake


def test_chat_returns_answer_trace_and_cost():
    api, _ = make([
        with_usage(tool_call_response("c1", "check_stock", {"product_id": "D002"})),
        with_usage(text_response("Sorry, it's sold out.")),
    ])
    sid = api.post("/api/session").json()["session_id"]
    body = api.post("/api/chat", json={"session_id": sid, "message": "Do you have water?"}).json()

    assert body["answer"] == "Sorry, it's sold out."
    assert body["trace"][0]["name"] == "check_stock"
    assert body["trace"][0]["result"]["stock"] == 0      # 工具结果以 JSON 对象返回给前端
    assert body["usage"]["calls"] == 2
    assert body["total"]["prompt_tokens"] == 200
    assert body["model"] == "fake-model"


def test_session_keeps_history_and_accumulates_cost():
    api, fake = make([with_usage(text_response("はい")), with_usage(text_response("150円です"))])
    sid = api.post("/api/session").json()["session_id"]
    api.post("/api/chat", json={"session_id": sid, "message": "お茶ありますか"})
    body = api.post("/api/chat", json={"session_id": sid, "message": "コーヒーは？"}).json()

    assert body["total"]["calls"] == 2
    # 第二轮请求里带着第一轮的对话
    contents = [m["content"] for m in fake.requests[1]["messages"]]
    assert "お茶ありますか" in contents and "はい" in contents


def test_sessions_are_isolated():
    api, _ = make([
        with_usage(tool_call_response("c1", "call_staff", {"reason": "返品", "language": "ja"})),
        with_usage(text_response("スタッフを呼びました")),
        with_usage(text_response("hi")),
    ])
    a = api.post("/api/session").json()["session_id"]
    b = api.post("/api/session").json()["session_id"]
    assert len(api.post("/api/chat", json={"session_id": a, "message": "返品したい"}).json()["staff_requests"]) == 1
    assert api.post("/api/chat", json={"session_id": b, "message": "hello"}).json()["staff_requests"] == []


def test_thinking_flag_is_passed_to_model():
    api, fake = make([with_usage(text_response("ok"))])
    sid = api.post("/api/session").json()["session_id"]
    api.post("/api/chat", json={"session_id": sid, "message": "hi", "thinking": True})
    assert fake.requests[0]["extra_body"] == {"thinking": {"type": "enabled"}}


def test_rejects_unknown_session_and_bad_input():
    api, _ = make([])
    assert api.post("/api/chat", json={"session_id": "nope", "message": "hi"}).status_code == 404
    sid = api.post("/api/session").json()["session_id"]
    assert api.post("/api/chat", json={"session_id": sid, "message": ""}).status_code == 422
    assert api.post("/api/chat", json={"session_id": sid, "message": "x" * 501}).status_code == 422
