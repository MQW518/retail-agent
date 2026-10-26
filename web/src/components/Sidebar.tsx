import type { StaffRequest, Usage } from '../api'

interface Props {
  model: string
  thinking: boolean
  onThinkingChange: (v: boolean) => void
  onNewSession: () => void
  total: Usage | null
  staff: StaffRequest[]
  disabled: boolean
}

export default function Sidebar({ model, thinking, onThinkingChange, onNewSession, total, staff, disabled }: Props) {
  return (
    <aside className="sidebar">
      <h2>🏪 无人便利店 AI 店员</h2>
      {model && <p className="muted">模型：{model}</p>}

      <label className="toggle" title="评测结果：开启后准确率没有提升，费用约 +40%，默认关闭">
        <input type="checkbox" checked={thinking} onChange={(e) => onThinkingChange(e.target.checked)} />
        思考模式
      </label>
      <button className="secondary" onClick={onNewSession} disabled={disabled}>
        新对话
      </button>

      <hr />
      <div className="metric">
        <span className="muted">本次会话费用（上限）</span>
        <strong>${(total?.cost_usd ?? 0).toFixed(5)}</strong>
      </div>
      <div className="metrics-row">
        <div className="metric">
          <span className="muted">模型调用</span>
          <strong>{total?.calls ?? 0}</strong>
        </div>
        <div className="metric">
          <span className="muted">token</span>
          <strong>{((total?.prompt_tokens ?? 0) + (total?.completion_tokens ?? 0)).toLocaleString()}</strong>
        </div>
      </div>

      <hr />
      <h3>转人工记录</h3>
      {staff.length === 0 ? (
        <p className="muted">暂无</p>
      ) : (
        <ul className="tickets">
          {staff.map((t) => (
            <li key={t.ticket}>
              <code>{t.ticket}</code> [{t.language}] {t.reason}
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
