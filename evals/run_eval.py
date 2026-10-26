"""用真实模型跑评测集。

python -m evals.run_eval              每题跑 1 次
python -m evals.run_eval --repeat 3   每题跑 3 次（模型输出有随机性，多跑几次更可靠）
python -m evals.run_eval --only p03   只跑某几题（逗号分隔）

结果保存在 evals/results/<时间>.json，终端打印每题结果和汇总。
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from agent.llm import make_client
from agent.loop import new_conversation, run_turn
from agent.tools import open_store
from evals.checks import check_case

HERE = Path(__file__).resolve().parent


def load_cases() -> list[dict]:
    lines = (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def run_case(client, model: str, case: dict) -> dict:
    store, messages = open_store(), new_conversation()
    start = time.time()
    trace: list = []
    answer = ""
    try:
        for user in case["turns"]:
            messages.append({"role": "user", "content": user})
            trace = []  # 只保留最后一轮的工具调用
            answer = run_turn(client, model, store, messages, trace)
        error = None
    except Exception as e:  # API 出错也记下来，不中断整个评测
        error = f"{type(e).__name__}: {e}"
    tools = [name for name, _, _ in trace]
    result = check_case(case, tools, answer) if error is None else {"pass": False}
    return {"id": case["id"], "cat": case["cat"], "lang": case["lang"], "answer": answer, "tools": tools,
            "tool_args": [args for _, args, _ in trace], "seconds": round(time.time() - start, 1),
            "error": error, **result}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cases = load_cases()
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    client, model = make_client()
    jobs = [c for c in cases for _ in range(args.repeat)]
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda c: run_case(client, model, c), jobs))

    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        flags = "" if r["pass"] else " ".join(k for k in ("tools_ok", "facts_ok", "no_forbidden", "lang_ok")
                                              if r.get(k) is False) or (r["error"] or "")
        print(f"{mark} {r['id']:4} {r['lang']} tools={r['tools']} {flags}\n     -> {r['answer'][:120]}")

    n = len(results)
    summary = {k: round(sum(bool(r.get(k)) for r in results) / n, 3)
               for k in ("pass", "tools_ok", "facts_ok", "no_forbidden", "lang_ok")}
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["cat"]].append(r["pass"])
    summary["by_category"] = {c: f"{sum(v)}/{len(v)}" for c, v in by_cat.items()}
    summary["avg_tool_calls"] = round(sum(len(r["tools"]) for r in results) / n, 2)
    summary["avg_seconds"] = round(sum(r["seconds"] for r in results) / n, 1)
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=1))

    out = HERE / "results" / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"model": model, "repeat": args.repeat, "summary": summary, "results": results},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
