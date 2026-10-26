"""DeepSeek 客户端。DeepSeek 兼容 OpenAI 的接口格式，所以直接用 openai SDK，只改 base_url。"""
import os

from dotenv import load_dotenv
from openai import OpenAI

BASE_URL = "https://api.deepseek.com"


def make_client() -> tuple[OpenAI, str]:
    load_dotenv()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY 未设置：把 .env.example 复制成 .env 并填入 key")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
    return OpenAI(api_key=key, base_url=BASE_URL), model
