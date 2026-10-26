"""HTTP 接口：把 Agent 主循环包成 API，供 React 前端调用。

.venv/Scripts/uvicorn server:app --port 8000

POST /api/session   新建会话，返回 session_id
POST /api/chat      发送一条消息，返回回答、本轮工具调用、本轮与会话累计的费用、转人工记录
构建好的前端（web/dist）也由这里提供，所以生产环境只需要启动这一个进程。
"""
import json
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.llm import make_client
from agent.loop import new_conversation, run_turn
from agent.tools import Store, open_store
from agent.usage import Usage

WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"
MAX_SESSIONS = 200  # 演示用：会话只放在内存里，超过上限时丢掉最早的


@dataclass
class Session:
    store: Store = field(default_factory=open_store)
    messages: list = field(default_factory=new_conversation)
    total: Usage = field(default_factory=Usage)
    lock: threading.Lock = field(default_factory=threading.Lock)  # 同一会话的请求按顺序处理


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=500)
    thinking: bool = False


def _add(total: Usage, part: Usage) -> None:
    for k in ("calls", "prompt_tokens", "cache_hit_tokens", "completion_tokens", "reasoning_tokens"):
        setattr(total, k, getattr(total, k) + getattr(part, k))


def create_app(client=None, model: str | None = None) -> FastAPI:
    """client / model 不传时用 .env 里的 DeepSeek 配置；测试时传入假的客户端。"""
    app = FastAPI(title="retail-agent")
    sessions: dict[str, Session] = {}
    sessions_lock = threading.Lock()
    llm: dict = {"client": client, "model": model}

    def get_llm():
        if llm["client"] is None:
            llm["client"], llm["model"] = make_client()
        return llm["client"], llm["model"]

    @app.post("/api/session")
    def new_session() -> dict:
        sid = uuid.uuid4().hex
        with sessions_lock:
            if len(sessions) >= MAX_SESSIONS:
                sessions.pop(next(iter(sessions)))
            sessions[sid] = Session()
        return {"session_id": sid}

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> dict:
        session = sessions.get(req.session_id)
        if session is None:
            raise HTTPException(404, "unknown session_id")
        client_, model_ = get_llm()
        with session.lock:
            session.messages.append({"role": "user", "content": req.message})
            trace: list = []
            usage = Usage()
            answer = run_turn(client_, model_, session.store, session.messages, trace, usage, req.thinking)
            _add(session.total, usage)
            return {
                "answer": answer,
                "trace": [{"name": n, "arguments": a, "result": json.loads(r)} for n, a, r in trace],
                "usage": usage.as_dict(),
                "total": session.total.as_dict(),
                "staff_requests": session.store.staff_requests,
                "model": model_,
            }

    if WEB_DIST.exists():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return app


app = create_app()
