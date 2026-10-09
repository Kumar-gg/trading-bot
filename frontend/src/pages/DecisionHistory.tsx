import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { DecisionType } from '../api/client'
import { fetchBots, fetchDecisions } from '../api/client'

const DECISIONS: DecisionType[] = ['BUY', 'SELL', 'HOLD', 'REJECTED']

function fmtTime(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function candleTime(ms: number | null) {
  if (!ms) return '—'
  return new Date(ms).toLocaleString()
}

export function DecisionHistory() {
  const { data: bots = [] } = useQuery({ queryKey: ['bots'], queryFn: fetchBots })
  const [botId, setBotId] = useState<number | ''>('')
  const [decision, setDecision] = useState<DecisionType | ''>('')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')
  const params = useMemo(
    () => ({
      bot_id: botId || undefined,
      decision: decision || undefined,
      since: since ? new Date(since).toISOString() : undefined,
      until: until ? new Date(until).toISOString() : undefined,
      limit: 200,
    }),
    [botId, decision, since, until],
  )
  const { data: logs = [], refetch, isFetching } = useQuery({
    queryKey: ['decisions', params],
    queryFn: () => fetchDecisions(params),
    refetchInterval: 15_000,
  })

  return (
    <div>
      <div className="page-header">
        <h1>Decision history</h1>
        <button type="button" className="btn" onClick={() => refetch()} disabled={isFetching}>
          Refresh
        </button>
      </div>
      <section className="panel filters">
        <label className="field">
          <span>Bot</span>
          <select value={botId} onChange={(e) => setBotId(e.target.value ? Number(e.target.value) : '')}>
            <option value="">All bots</option>
            {bots.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Decision</span>
          <select value={decision} onChange={(e) => setDecision((e.target.value || '') as DecisionType | '')}>
            <option value="">All</option>
            {DECISIONS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Since (local)</span>
          <input type="datetime-local" value={since} onChange={(e) => setSince(e.target.value)} />
        </label>
        <label className="field">
          <span>Until (local)</span>
          <input type="datetime-local" value={until} onChange={(e) => setUntil(e.target.value)} />
        </label>
      </section>
      <section className="panel">
        <table className="decision-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Bot</th>
              <th>Decision</th>
              <th>Candle</th>
              <th>BTC</th>
              <th>Data age</th>
              <th>Reason</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => {
              const bot = bots.find((b) => b.id === log.bot_id)
              return (
                <tr key={log.id}>
                  <td>{fmtTime(log.evaluated_at)}</td>
                  <td>
                    <Link to={`/bots/${log.bot_id}`}>{bot?.name ?? `#${log.bot_id}`}</Link>
                  </td>
                  <td><span className={`decision-pill ${log.decision}`}>{log.decision}</span></td>
                  <td>{candleTime(log.candle_open_time)}</td>
                  <td>{log.btc_price?.toFixed(2) ?? '—'}</td>
                  <td>{log.market_data_age_sec != null ? `${log.market_data_age_sec.toFixed(0)}s` : '—'}</td>
                  <td>{log.reason}</td>
                  <td>
                    <details>
                      <summary>Conditions</summary>
                      <p className="muted">Indicators: {JSON.stringify(log.indicators)}</p>
                      <ul className="cond-list">
                        {[...log.entry_conditions, ...log.exit_conditions].map((c) => (
                          <li key={c.name} className={c.passed ? 'pass' : 'fail'}>
                            {c.name}: {c.passed ? 'PASS' : 'FAIL'} — {c.detail}
                          </li>
                        ))}
                      </ul>
                      {log.rejection_detail && (
                        <p className="neg">Rejected ({log.rejection_source}): {log.rejection_detail}</p>
                      )}
                    </details>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!logs.length && <p className="muted">No decisions yet. Start a bot and wait for the next closed candle.</p>}
      </section>
    </div>
  )
}
