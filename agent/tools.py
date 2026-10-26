"""Agent 可以调用的工具。

每个工具由两部分组成：
1. 给模型看的「说明书」（TOOL_SCHEMAS，JSON Schema 格式），模型据此决定调用哪个、传什么参数；
2. 真正执行的 Python 函数。

模型给的参数不可信（官方文档也提醒可能不是合法 JSON、或带多余字段），
所以 execute_tool 统一做校验，出错时把错误信息作为工具结果还给模型，而不是让程序崩掉。
"""
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from . import db
from .rag import PolicyIndex, load_sections

CATEGORIES = ["food", "drink", "daily", "electronics"]
LANGUAGES = ["ja", "zh", "en"]


@dataclass
class Store:
    """工具运行时需要的全部状态：商品数据库、店铺规定索引、转人工记录。"""
    conn: sqlite3.Connection
    policy: PolicyIndex
    staff_requests: list[dict] = field(default_factory=list)


def open_store() -> Store:
    return Store(conn=db.connect(), policy=PolicyIndex(load_sections()))


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search store products by keyword in Japanese, Chinese or English. "
                "Returns id, names, price (JPY, tax included) and shelf location. "
                "Use this before answering any question about what the store sells or prices."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": (
                            "Product keyword, e.g. 'お茶', '雨伞', 'charger'. Use a short noun. "
                            "Search with the customer's own words first (names are stored in ja/zh/en); "
                            "only try other languages or synonyms if that returns nothing."
                        ),
                    },
                    "category": {
                        "type": "string",
                        "enum": CATEGORIES,
                        "description": "Optional category filter.",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Get the current stock count of one product by its id (from search_products).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product id such as 'D001'."},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_store_policy",
            "description": (
                "Search the store guide (opening hours, entry, payment methods, receipts, returns, tax-free, "
                "alcohol/tobacco, microwave/hot water, eat-in, trash, toilet, Wi-Fi, lost items, staff call, cameras). "
                "The guide is written in Japanese, so ALWAYS write the query in Japanese keywords, "
                "even if the customer asked in Chinese or English (e.g. '支払い Alipay', 'トイレ', '返品')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Japanese keywords."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_staff",
            "description": (
                "Call a remote staff member. Use when the customer asks for a return/refund, lost items, "
                "has an emergency or trouble, explicitly asks for a person, "
                "or asks something that neither the products nor the store guide can answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Short summary of the customer's request, in Japanese."},
                    "language": {"type": "string", "enum": LANGUAGES, "description": "Customer's language."},
                },
                "required": ["reason", "language"],
            },
        },
    },
]


def search_products(store: Store, keyword: str, category: str | None = None) -> list[dict]:
    like = f"%{keyword.strip()}%"
    sql = (
        "SELECT id, name_ja, name_zh, name_en, category, price_jpy, shelf FROM products "
        # 名称之外也查 aliases（「お茶」「水」这类日常叫法）；SQLite 的 LIKE 对英文默认不区分大小写
        "WHERE (name_ja LIKE ? OR name_zh LIKE ? OR name_en LIKE ? OR aliases LIKE ?)"
    )
    args: list = [like, like, like, like]
    if category:
        sql += " AND category = ?"
        args.append(category)
    return [dict(r) for r in store.conn.execute(sql, args).fetchall()]


def check_stock(store: Store, product_id: str) -> dict:
    row = store.conn.execute(
        "SELECT id, name_ja, stock FROM products WHERE id = ?", (product_id.strip().upper(),)
    ).fetchone()
    if row is None:
        return {"error": f"unknown product_id: {product_id}"}
    return dict(row)


def search_store_policy(store: Store, query: str) -> dict:
    hits = store.policy.search(query)
    if not hits:
        return {"results": [], "note": "No matching section in the store guide."}
    return {"results": hits}


def call_staff(store: Store, reason: str, language: str) -> dict:
    # 演示版：只记录下来。真实店铺这里会推送到远程客服系统。
    ticket = {"ticket": f"S{len(store.staff_requests) + 1:03d}", "reason": reason, "language": language,
              "time": datetime.now().isoformat(timespec="seconds")}
    store.staff_requests.append(ticket)
    return {"status": "staff notified", "ticket": ticket["ticket"]}


_FUNCTIONS = {
    "search_products": search_products,
    "check_stock": check_stock,
    "search_store_policy": search_store_policy,
    "call_staff": call_staff,
}
_SCHEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOL_SCHEMAS}


def execute_tool(store: Store, name: str, arguments_json: str) -> str:
    """执行一次工具调用，返回给模型的字符串（JSON）。任何错误都转成 {"error": ...}。"""
    func = _FUNCTIONS.get(name)
    if func is None:
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
    try:
        args = json.loads(arguments_json or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        return json.dumps({"error": f"invalid arguments: {e}"}, ensure_ascii=False)

    schema = _SCHEMAS[name]
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing:
        return json.dumps({"error": f"missing required arguments: {missing}"}, ensure_ascii=False)
    # 只保留 schema 里声明过的参数，丢掉模型多给的字段；enum 参数检查取值
    args = {k: v for k, v in args.items() if k in schema["properties"]}
    for k, v in args.items():
        allowed = schema["properties"][k].get("enum")
        if allowed and v not in allowed:
            return json.dumps({"error": f"{k} must be one of {allowed}"}, ensure_ascii=False)

    try:
        result = func(store, **args)
    except Exception as e:  # 工具内部出错也不能让整个对话崩掉
        result = {"error": f"{type(e).__name__}: {e}"}
    return json.dumps(result, ensure_ascii=False)
