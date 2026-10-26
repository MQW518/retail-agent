"""语言判断（日 / 中 / 英），不调用模型。

- detect_customer_lang：判断顾客提问的语言，主循环据此明确告诉模型用哪种语言回答；
- detect_answer_lang：判断回答的语言，评测用。
"""
import re

_HIRA = re.compile(r"[぀-ゟ]")
_HAN = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
_QUOTED = re.compile(r"（[^）]*）|\([^)]*\)|「[^」]*」")

LANG_NAMES = {"ja": "Japanese", "zh": "Chinese (Simplified)", "en": "English"}


def detect_customer_lang(text: str) -> str:
    """顾客的提问通常很短：有平假名就是日语；没有平假名但有汉字就是中文（如「緑茶 多少钱？」）；否则英语。"""
    if _HIRA.search(text):
        return "ja"
    if _HAN.search(text):
        return "zh"
    return "en"


def detect_answer_lang(text: str) -> str:
    """判断回答的语言。

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
