import json
from pathlib import Path

import pytest

from agent.lang import detect_answer_lang, detect_customer_lang
from evals.checks import check_case


@pytest.mark.parametrize("text,lang", [
    ("緑茶 500ml は 140円（税込）です。C-1の棚にありますよ。", "ja"),
    ("充电宝（モバイルバッテリー）还有 3 个，价格 2,980 日元。", "zh"),  # 中文里夹日语商品名
    ("有的，饭团（おにぎり 鮭）160日元，在 A-1 货架。", "zh"),
    ("Yes, mineral water is ¥110 but it's sold out.", "en"),
])
def test_detect_answer_lang(text, lang):
    assert detect_answer_lang(text) == lang


@pytest.mark.parametrize("text,lang", [
    ("お茶ありますか", "ja"),
    ("緑茶 多少钱？", "zh"),            # 中文里夹日语商品名
    ("モバイルバッテリー还有吗", "zh"),
    ("雨伞便宜点，500日元卖给我吧", "zh"),
    ("do u hav umbrela", "en"),
])
def test_detect_customer_lang(text, lang):
    assert detect_customer_lang(text) == lang


def test_check_case():
    case = {"lang": "en", "tools_all": ["search_products", "check_stock"],
            "facts": [["sold out", "out of stock"]], "forbid_text": ["sandwich"]}
    ok = check_case(case, ["search_products", "check_stock"], "Sorry, it's Sold Out.")
    assert ok["pass"]
    assert not check_case(case, ["search_products"], "Sorry, it's sold out.")["tools_ok"]
    assert not check_case(case, ["search_products", "check_stock"], "We have it!")["facts_ok"]
    assert not check_case(case, ["search_products", "check_stock"], "Sold out. Try a sandwich?")["no_forbidden"]


def test_cases_file_is_valid():
    path = Path(__file__).resolve().parent.parent / "evals" / "cases.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        assert c["lang"] in {"ja", "zh", "en"} and c["turns"] and c.get("facts")
