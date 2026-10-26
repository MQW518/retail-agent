import json

import pytest

from agent.tools import check_stock, execute_tool, open_store, search_products


@pytest.fixture
def store():
    return open_store()


@pytest.mark.parametrize("keyword,expected_id", [
    ("緑茶", "D001"),      # 日语
    ("雨伞", "H001"),      # 中文
    ("umbrella", "H001"),  # 英语
    ("UMBRELLA", "H001"),  # 英语大小写不敏感
    ("お茶", "D001"),      # 别名：日常叫法（第一次真实对话里搜不到的词）
    ("充電器", "E001"),
])
def test_search_multilingual(store, keyword, expected_id):
    assert expected_id in [p["id"] for p in search_products(store, keyword)]


def test_search_category_filter(store):
    assert search_products(store, "おにぎり", category="drink") == []


def test_check_stock(store):
    assert check_stock(store, "d002")["stock"] == 0
    assert "error" in check_stock(store, "X999")


@pytest.mark.parametrize("query,expected_title", [
    ("支払い Alipay", "お支払い方法"),
    ("現金", "お支払い方法"),
    ("返品", "返品・交換"),
    ("お湯 カップラーメン", "電子レンジ・お湯"),
    ("トイレ", "トイレ"),
])
def test_policy_search_top1(store, query, expected_title):
    out = json.loads(execute_tool(store, "search_store_policy", json.dumps({"query": query}, ensure_ascii=False)))
    assert out["results"][0]["title"] == expected_title


def test_policy_search_no_hit(store):
    out = json.loads(execute_tool(store, "search_store_policy", '{"query": "駐車場"}'))
    assert out["results"] == []


def test_call_staff_records_ticket(store):
    out = json.loads(execute_tool(store, "call_staff", '{"reason": "返品希望", "language": "zh"}'))
    assert out["ticket"] == "S001"
    assert store.staff_requests[0]["language"] == "zh"


def test_execute_tool_rejects_bad_input(store):
    assert "error" in json.loads(execute_tool(store, "no_such_tool", "{}"))
    assert "error" in json.loads(execute_tool(store, "check_stock", "not json"))
    assert "error" in json.loads(execute_tool(store, "check_stock", "{}"))
    assert "error" in json.loads(execute_tool(store, "search_products", '{"keyword": "茶", "category": "toys"}'))
    assert "error" in json.loads(execute_tool(store, "call_staff", '{"reason": "x", "language": "fr"}'))


def test_execute_tool_drops_extra_arguments(store):
    out = json.loads(execute_tool(store, "check_stock", '{"product_id": "D001", "extra": 1}'))
    assert out["stock"] == 30


def test_store_usable_from_another_thread(store):
    """回归测试：网页界面里工具会在别的线程执行（曾因 SQLite 线程限制全部报错）。"""
    import threading
    out = []
    t = threading.Thread(target=lambda: out.append(execute_tool(store, "search_products", '{"keyword": "water"}')))
    t.start()
    t.join()
    assert "error" not in json.loads(out[0])
