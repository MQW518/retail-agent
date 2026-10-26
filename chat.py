"""命令行对话：python chat.py   （加 --trace 显示每次工具调用）"""
import sys

from agent.llm import make_client
from agent.loop import new_conversation, run_turn
from agent.tools import open_store


def main() -> None:
    show_trace = "--trace" in sys.argv
    client, model = make_client()
    store = open_store()
    messages = new_conversation()
    print(f"[{model}] 便利店 AI 店员。输入 exit 退出。")
    while True:
        try:
            user = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        trace: list = []
        answer = run_turn(client, model, store, messages, trace)
        if show_trace:
            for name, args, result in trace:
                print(f"  [tool] {name}({args}) -> {result}")
        print(f"店员: {answer}")


if __name__ == "__main__":
    main()
