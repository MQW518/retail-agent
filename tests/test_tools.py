import json

import pytest

from agent.db import connect
from agent.tools import check_stock, execute_tool, search_products


@pytest.fixture
def conn():
    return connect()


@pytest.mark.parametrize("keyword,expected_id", [
    ("緑茶", "D001"),      # 日语
    ("雨伞", "H001"),      # 中文
    ("umbrella", "H001"),  # 英语
    ("UMBRELLA", "H001"),  # 英语大小写不敏感
])
def test_search_multilingual(conn, keyword, expected_id):
    assert expected_id in [p["id"] for p in search_products(conn, keyword)]


def test_search_category_filter(conn):
    ids = [p["id"] for p in search_products(conn, "おにぎり", category="drink")]
    assert ids == []


def test_check_stock(conn):
    assert check_stock(conn, "d002")["stock"] == 0
    assert "error" in check_stock(conn, "X999")


def test_execute_tool_rejects_bad_input(conn):
    assert "error" in json.loads(execute_tool(conn, "no_such_tool", "{}"))
    assert "error" in json.loads(execute_tool(conn, "check_stock", "not json"))
    assert "error" in json.loads(execute_tool(conn, "check_stock", "{}"))
    assert "error" in json.loads(execute_tool(conn, "search_products", '{"keyword": "茶", "category": "toys"}'))


def test_execute_tool_drops_extra_arguments(conn):
    out = json.loads(execute_tool(conn, "check_stock", '{"product_id": "D001", "extra": 1}'))
    assert out["stock"] == 30
