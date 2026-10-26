"""店铺规定的检索（RAG 里的 R）。

文档很短（十几个小节），所以没有用向量检索，而是：
- 按「## 标题」切成段落；
- 文本做 NFKC 规范化后切成字符 bigram（日语没有空格，按字切最稳）；
- 用 BM25 给每段打分，返回分数最高的几段。

跨语言的问题交给模型：工具说明要求模型把顾客的问题改写成日语查询词再调用。
"""
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "data" / "store_policy_ja.md"

K1, B = 1.5, 0.75  # BM25 的标准参数


def _normalize(text: str) -> str:
    # NFKC：全角英数→半角等；再转小写，去掉标点和空白
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s、。，．・「」（）()：:？?！!\-#]+", "", text)


def _bigrams(text: str) -> list[str]:
    t = _normalize(text)
    if len(t) < 2:
        return [t] if t else []
    return [t[i:i + 2] for i in range(len(t) - 1)]


def load_sections(path: Path = DOC) -> list[dict]:
    sections = []
    for block in path.read_text(encoding="utf-8").split("\n## ")[1:]:
        title, _, body = block.partition("\n")
        sections.append({"title": title.strip(), "text": body.strip()})
    return sections


class PolicyIndex:
    def __init__(self, sections: list[dict]):
        self.sections = sections
        # 标题也参与检索（标题本身就是很强的关键词）
        self.docs = [Counter(_bigrams(s["title"] + s["text"])) for s in sections]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths)
        df = Counter(term for d in self.docs for term in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        q_terms = set(_bigrams(query))
        scored = []
        for sec, doc, length in zip(self.sections, self.docs, self.lengths):
            score = 0.0
            for t in q_terms:
                tf = doc.get(t, 0)
                if tf:
                    score += self.idf[t] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / self.avg_len))
            if score > 0:
                scored.append((score, sec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"title": s["title"], "text": s["text"], "score": round(sc, 2)} for sc, s in scored[:top_k]]
