import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useEffect } from 'react'
import { Line, LineChart, ResponsiveContainer } from 'recharts'
import { fetchBots } from '../api/client'

function healthLabel(status: string | undefined, botStatus: string) {
  if (botStatus !== 'running') return { text: 'Not evaluating', cls: 'idle' }
  if (status === 'active') return { text: 'Evaluating live', cls: 'active' }
  if (status === 'stale') return { text: 'Stale — no recent eval', cls: 'stale' }
  if (status === 'error') return { text: 'Error', cls: 'error' }
  return { text: 'Waiting…', cls: 'stale' }
}

function fmtTime(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function Dashboard() {
  const qc = useQueryClient()
  const { data: bots = [], isLoading, isError } = useQuery({
    queryKey: ['bots'],
    queryFn: fetchBots,
    refetchInterval: 10_000,
    retry: 1,
  })

  useEffect(() => {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/stream`)
    ws.onmessage = () => {
      qc.invalidateQueries({ queryKey: ['bots'] })
      qc.invalidateQueries({ queryKey: ['decisions'] })
    }
    return () => ws.close()
  }, [qc])

  if (isLoading) return <p>Loading bots...</p>
  if (isError) return <p className="neg">Could not load bots. Restart the API or run backend migration.</p>

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <Link to="/bots/new" className="btn primary">New bot</Link>
      </div>
      <div className="bot-grid">
        {bots.map((bot) => {
          const health = healthLabel(bot.health_status, bot.status)
          return (
            <Link key={bot.id} to={`/bots/${bot.id}`} className="bot-card">
              <div className="bot-card-head">
                <strong>{bot.name}</strong>
                <span className={`status-pill ${bot.status}`}>{bot.status}</span>
              </div>
              <div className={`health-pill ${health.cls}`}>{health.text}</div>
              <div className="muted">{bot.symbol} · {bot.timeframe} · {bot.template_id}</div>
              <div className="decision-row">
                <span className={`decision-pill ${bot.latest_decision ?? 'HOLD'}`}>
                  {bot.latest_decision ?? '—'}
                </span>
                <span className="muted decision-reason">{bot.latest_decision_reason ?? 'No evaluation yet'}</span>
              </div>
              <div className="muted eval-line">Last eval: {fmtTime(bot.last_evaluation_at)}</div>
              <div className="muted eval-line">Market data: {fmtTime(bot.last_market_data_at)}</div>
              {bot.last_eval_error && bot.status === 'running' && (
                <div className="neg eval-line">{bot.last_eval_error}</div>
              )}
              <div className="metrics">
                <div>
                  <label>Equity</label>
                  <span>{bot.equity?.toFixed(2) ?? '—'}</span>
                </div>
                <div>
                  <label>Return</label>
                  <span className={((bot.return_pct ?? 0) >= 0) ? 'pos' : 'neg'}>
                    {bot.return_pct?.toFixed(2) ?? '0.00'}%
                  </span>
                </div>
                <div>
                  <label>Position</label>
                  <span>{bot.position_qty?.toFixed(6) ?? '0'}</span>
                </div>
              </div>
              <div className="spark">
                <ResponsiveContainer width="100%" height={48}>
                  <LineChart data={[{ v: bot.return_pct ?? 0 }, { v: (bot.return_pct ?? 0) * 0.9 }, { v: bot.return_pct ?? 0 }]}>
                    <Line type="monotone" dataKey="v" stroke="#3b82f6" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Link>
          )
        })}
      </div>
      {!bots.length && <p>No bots yet. Create one to start paper trading.</p>}
    </div>
  )
}
