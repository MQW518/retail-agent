"""商品数据库：每次启动都从 data/seed.sql 建一个内存 SQLite，保证结果可复现。"""
import sqlite3
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed.sql"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # 让查询结果可以按列名取值
    conn.executescript(SEED.read_text(encoding="utf-8"))
    return conn
