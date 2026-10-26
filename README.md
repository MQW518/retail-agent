# retail-agent

多语言（日 / 中 / 英）无人便利店 AI 店员 Agent。**开发中。**

顾客用任意语言提问，Agent 通过 Tool Calling 查询商品数据库，再用同一种语言回答。
Agent 主循环是手写的（不依赖 LangChain 等框架），LLM 使用 DeepSeek API（OpenAI 兼容格式）。

## 现在能做什么
- 多轮对话，自动用顾客的语言回答
- 工具：`search_products`（三语商品检索、价格、货架位置）、`check_stock`（库存）
- 工具参数校验：非法 JSON、缺参数、多余参数、未知工具都会作为错误结果返回给模型，而不是让程序崩溃
- 步数上限：防止模型无限循环调用工具
- 离线测试：用假的模型客户端测试主循环，不消耗 API 费用

## 运行
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
cp .env.example .env    # 填入 DEEPSEEK_API_KEY
.venv/Scripts/python chat.py --trace
.venv/Scripts/python -m pytest -q
```

## 结构
```
agent/loop.py    Agent 主循环：模型 → tool_calls → 执行工具 → 结果回传 → 模型
agent/tools.py   工具的 JSON Schema 和实现、参数校验
agent/db.py      从 data/seed.sql 建内存 SQLite（商品数据为虚构）
agent/llm.py     DeepSeek 客户端
chat.py          命令行对话
tests/           离线测试
```

## 设计记录
- **关闭思考模式**：`deepseek-flash` 默认开启思考模式，而带 tools 的多轮请求在思考模式下必须把 `reasoning_content` 原样回传。
  第一版先关闭（`thinking: disabled`），主循环更简单，响应也更快。

## 计划
- [ ] RAG：检索日语的店铺规定 / FAQ 文档
- [ ] 转人工工具
- [ ] 评测集（三语测试问题）+ 评测脚本：工具选择正确率、回答正确率
