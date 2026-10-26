"""评测的判定规则（纯函数，不调用模型，可以单独测试）。

每道题只看最后一轮：最后一轮调用了哪些工具、最后一轮的回答。
"""
from agent.lang import detect_answer_lang


def check_case(case: dict, tools_called: list[str], answer: str) -> dict:
    low = answer.lower()
    tools_ok = all(t in tools_called for t in case.get("tools_all", []))
    if case.get("tools_any"):
        tools_ok = tools_ok and any(t in tools_called for t in case["tools_any"])
    # facts：每一组里至少出现一个词（同一个意思的不同说法放在一组）
    facts_ok = all(any(w.lower() in low for w in group) for group in case.get("facts", []))
    no_forbidden = not any(w.lower() in low for w in case.get("forbid_text", []))
    lang_ok = detect_answer_lang(answer) == case["lang"]
    return {
        "tools_ok": tools_ok,
        "facts_ok": facts_ok,
        "no_forbidden": no_forbidden,
        "lang_ok": lang_ok,
        "pass": tools_ok and facts_ok and no_forbidden and lang_ok,
    }
