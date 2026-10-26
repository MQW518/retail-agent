import type { Turn } from '../App'

// 一轮对话：顾客提问 + 店员回答 + 可展开的工具调用明细
export default function TurnView({ turn }: { turn: Turn }) {
  return (
    <div className="turn">
      <div className="bubble user">{turn.user}</div>
      {turn.error ? (
        <div className="bubble error">出错了：{turn.error}</div>
      ) : turn.answer === undefined ? (
        <div className="bubble agent pending">思考中…</div>
      ) : (
        <div className="bubble agent">
          <p>{turn.answer}</p>
          {turn.trace && turn.usage && (
            <details>
              <summary>
                工具调用 {turn.trace.length} 次 · 模型调用 {turn.usage.calls} 次 · ${turn.usage.cost_usd.toFixed(5)}
              </summary>
              {turn.trace.length === 0 && <p className="muted">本轮没有调用工具</p>}
              {turn.trace.map((call, i) => (
                <div key={i} className="tool">
                  <code className="tool-name">{call.name}</code>
                  <code>{call.arguments}</code>
                  <pre>{JSON.stringify(call.result, null, 2)}</pre>
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  )
}
