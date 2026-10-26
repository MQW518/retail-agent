"""商品数据库：每次启动都从 data/seed.sql 建一个内存 SQLite，保证结果可复现。"""
import sqlite3
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed.sql"


def connect() -> sqlite3.Connection:
    # check_same_thread=False：Streamlit 每次刷新可能在不同线程里运行，默认设置下会报 ProgrammingError。
    # 对话中只读不写，跨线程使用是安全的。
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 让查询结果可以按列名取值
    conn.executescript(SEED.read_text(encoding="utf-8"))
    return conn
