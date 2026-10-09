import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import {
  botAction,
  fetchBot,
  fetchJournal,
  fetchRuns,
  fetchStrategies,
  updateBot,
} from '../api/client'
import { BotParamForm } from '../components/BotParamForm'
import { StrategyPicker } from '../components/StrategyPicker'
import { BotControlBar } from '../components/BotControlBar'
import { formatEventTime } from '../utils/formatTime'

export function BotDetail() {
  const { id } = useParams()
  const botId = Number(id)
  const nav = useNavigate()
  const qc = useQueryClient()

  const { data: bot } = useQuery({ queryKey: ['bot', botId], queryFn: () => fetchBot(botId), enabled: !!botId })
  const { data: strategies = [] } = useQuery({ queryKey: ['strategies'], queryFn: fetchStrategies })
  const { data: runs = [] } = useQuery({ queryKey: ['runs', botId], queryFn: () => fetchRuns(botId), enabled: !!botId })
  const activeRunId = bot?.current_run_id
  const { data: journal = [] } = useQuery({
    queryKey: ['journal', activeRunId],
    queryFn: () => fetchJournal(activeRunId!),
    enabled: !!activeRunId,
    refetchInterval: 20_000,
  })

  const strategy = strategies.find((s) => s.id === (bot?.template_id ?? 'ema_trend'))
  const [params, setParams] = useState<Record<string, unknown>>({})
  const [name, setName] = useState('')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState('5m')
  const [templateId, setTemplateId] = useState('ema_trend')

  useEffect(() => {
    if (!bot) return
    setParams(bot.params ?? {})
    setName(bot.name)
    setSymbol(bot.symbol)
    setTimeframe(bot.timeframe)
    setTemplateId(bot.template_id)
  }, [bot])

  const schema = useMemo(() => (strategy?.params_schema ?? {}) as Record<string, unknown>, [strategy])

  const saveMut = useMutation({
    mutationFn: () => updateBot(botId, { name, symbol, timeframe, template_id: templateId, params }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bot', botId] }),
  })

  const actionMut = useMutation({
    mutationFn: (action: 'start' | 'pause' | 'stop' | 'reset') => botAction(botId, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bot', botId] })
      qc.invalidateQueries({ queryKey: ['bots'] })
      qc.invalidateQueries({ queryKey: ['runs', botId] })
    },
  })

  if (!bot) return <p>Loading...</p>

  return (
    <div>
      <Link to="/">← Dashboard</Link>
      <div className="page-header">
        <h1>{bot.name}</h1>
      </div>

      <section className="panel panel-controls">
        <BotControlBar
          status={bot.status}
          busy={actionMut.isPending}
          onAction={(action) => actionMut.mutate(action)}
        />
      </section>

      <section className="panel">
        <h2>Status</h2>
        <p>
          <span className={`status-pill ${bot.status}`}>{bot.status}</span>
          {' '}· Run #{bot.current_run_id} · Return {bot.return_pct?.toFixed(2)}%
        </p>
        <p>Equity: {bot.equity?.toFixed(2)} · Position: {bot.position_qty ?? 0}</p>
        <button className="btn linkish" onClick={() => nav(`/journal/${activeRunId}`)} disabled={!activeRunId}>
          Open full journal
        </button>
      </section>

      <section className="panel">
        <h2>Configuration</h2>
        <label className="field"><span>Name</span><input value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field"><span>Symbol</span><input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} /></label>
        <label className="field">
          <span>Timeframe</span>
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            {(strategy?.supported_timeframes ?? ['5m']).map((tf) => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </label>
        <StrategyPicker strategies={strategies} value={templateId} onChange={setTemplateId} />
        <BotParamForm schema={schema as never} values={params} onChange={setParams} />
        <button className="btn primary" onClick={() => saveMut.mutate()} disabled={bot.status === 'running'}>
          Save (pause bot first)
        </button>
      </section>

      <section className="panel">
        <h2>Recent journal</h2>
        <table>
          <thead><tr><th>Time</th><th>Type</th><th>Message</th></tr></thead>
          <tbody>
            {journal.slice(0, 15).map((e) => (
              <tr key={e.id}>
                <td>{formatEventTime(e.created_at)}</td>
                <td>{e.event_type}</td>
                <td>{e.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Past runs</h2>
        <ul>
          {runs.map((r) => (
            <li key={r.id}>
              Run #{r.id} · {r.template_id} · {new Date(r.started_at).toLocaleString()}
              {r.ended_at ? ' (archived)' : ' (active)'}
              {' '}
              <Link to={`/journal/${r.id}`}>Journal</Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
