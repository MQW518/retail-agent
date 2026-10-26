"""评测的判定规则（纯函数，不调用模型，可以单独测试）。

每道题只看最后一轮：最后一轮调用了哪些工具、最后一轮的回答。
"""
import re

_HIRA = re.compile(r"[぀-ゟ]")
_HAN = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
_QUOTED = re.compile(r"（[^）]*）|\([^)]*\)|「[^」]*」")


def detect_lang(text: str) -> str:
    """粗略判断回答的语言。

    日语回答里平假名很多；中文回答可能引用日语商品名（含少量假名），所以用平假名占比而不是「有没有假名」，
    并且先去掉括号 / 引号里的内容（商品名通常写在那里）。
    """
    text = _QUOTED.sub("", text)
    hira, han, latin = len(_HIRA.findall(text)), len(_HAN.findall(text)), len(_LATIN.findall(text))
    if hira >= 3 and hira / (hira + han) > 0.2:
        return "ja"
    if han > 0 and han * 4 >= latin:
        return "zh"
    return "en"


def check_case(case: dict, tools_called: list[str], answer: str) -> dict:
    low = answer.lower()
    tools_ok = all(t in tools_called for t in case.get("tools_all", []))
    if case.get("tools_any"):
        tools_ok = tools_ok and any(t in tools_called for t in case["tools_any"])
    # facts：每一组里至少出现一个词（同一个意思的不同说法放在一组）
    facts_ok = all(any(w.lower() in low for w in group) for group in case.get("facts", []))
    no_forbidden = not any(w.lower() in low for w in case.get("forbid_text", []))
    lang_ok = detect_lang(answer) == case["lang"]
    return {
        "tools_ok": tools_ok,
        "facts_ok": facts_ok,
        "no_forbidden": no_forbidden,
        "lang_ok": lang_ok,
        "pass": tools_ok and facts_ok and no_forbidden and lang_ok,
    }
