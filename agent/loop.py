"""手写的 Agent 主循环（不用 LangChain 等框架）。

一轮用户提问的处理流程：
  1. 把对话历史 + 工具说明书发给模型；
  2. 模型要么直接回答，要么返回 tool_calls（想调用哪些工具、参数是什么）；
  3. 如果是 tool_calls：逐个执行工具，把结果以 role="tool" 消息追加到历史，回到第 1 步；
  4. 直到模型给出文字回答，或者超过 max_steps（防止模型无限调工具）。
"""
import sqlite3

from .tools import TOOL_SCHEMAS, execute_tool

SYSTEM_PROMPT = """You are the clerk assistant of an unstaffed convenience store in Tokyo.
Rules:
- Always reply in the same language as the customer's latest message (Japanese, Chinese or English).
- For any question about products, prices, shelf locations or stock, call the tools first. Never guess.
- When the customer asks whether the store has an item, also call check_stock before answering: a product with stock 0 is sold out.
- Prices are in JPY and include tax.
- If the tools return no result, say the store does not carry it.
- Only mention products that a tool has returned in this conversation. Never suggest other items from general knowledge.
- Keep answers short and friendly."""

MAX_STEPS = 5


def run_turn(client, model: str, conn: sqlite3.Connection, messages: list[dict], trace: list | None = None) -> str:
    """处理一轮用户输入。messages 会被原地追加（assistant / tool 消息），以保留多轮上下文。

    trace 不为 None 时，记录每次工具调用 (name, arguments, result)，供评测和调试使用。
    """
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            # 关闭思考模式：开着时，带 tools 的多轮请求必须把 reasoning_content 原样回传，
            # 小版本先关掉，逻辑更简单，也更快更便宜。
            extra_body={"thinking": {"type": "disabled"}},
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            answer = msg.content or ""
            messages.append({"role": "assistant", "content": answer})
            return answer

        # 先把「模型决定调用工具」这条 assistant 消息原样放回历史，
        # 后面的 tool 消息要用 tool_call_id 和它一一对应。
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            result = execute_tool(conn, tc.function.name, tc.function.arguments)
            if trace is not None:
                trace.append((tc.function.name, tc.function.arguments, result))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    # 超过步数上限：不再调用模型，直接给出兜底回答
    fallback = "Sorry, I could not finish this request. Please ask a staff member."
    messages.append({"role": "assistant", "content": fallback})
    return fallback


def new_conversation() -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}]
