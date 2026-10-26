"""Agent 可以调用的工具。

每个工具由两部分组成：
1. 给模型看的「说明书」（TOOL_SCHEMAS，JSON Schema 格式），模型据此决定调用哪个、传什么参数；
2. 真正执行的 Python 函数。

模型给的参数不可信（官方文档也提醒可能不是合法 JSON、或带多余字段），
所以 execute_tool 统一做校验，出错时把错误信息作为工具结果还给模型，而不是让程序崩掉。
"""
import json
import sqlite3

CATEGORIES = ["food", "drink", "daily", "electronics"]

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
                        "description": "Product keyword, e.g. 'お茶', '雨伞', 'charger'. Use a short noun.",
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
]


def search_products(conn: sqlite3.Connection, keyword: str, category: str | None = None) -> list[dict]:
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
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def check_stock(conn: sqlite3.Connection, product_id: str) -> dict:
    row = conn.execute("SELECT id, name_ja, stock FROM products WHERE id = ?", (product_id.strip().upper(),)).fetchone()
    if row is None:
        return {"error": f"unknown product_id: {product_id}"}
    return dict(row)


_FUNCTIONS = {"search_products": search_products, "check_stock": check_stock}


def execute_tool(conn: sqlite3.Connection, name: str, arguments_json: str) -> str:
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

    # 只保留 schema 里声明过的参数，丢掉模型多给的字段
    schema = next(t["function"]["parameters"] for t in TOOL_SCHEMAS if t["function"]["name"] == name)
    allowed = schema["properties"].keys()
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing:
        return json.dumps({"error": f"missing required arguments: {missing}"}, ensure_ascii=False)
    args = {k: v for k, v in args.items() if k in allowed}
    if args.get("category") not in (None, *CATEGORIES):
        return json.dumps({"error": f"category must be one of {CATEGORIES}"}, ensure_ascii=False)

    try:
        result = func(conn, **args)
    except Exception as e:  # 工具内部出错也不能让整个对话崩掉
        result = {"error": f"{type(e).__name__}: {e}"}
    return json.dumps(result, ensure_ascii=False)
