import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMemo, useState } from 'react'
import type { JournalEvent } from '../api/client'
import { fetchBots, fetchJournalEvents } from '../api/client'
import { formatCandleTime, formatEventTime } from '../utils/formatTime'

const EVENT_TYPES = [
  'regime_change',
  'strategy_evaluation',
  'decision',
  'signal',
  'risk_rejected',
  'order_placed',
  'fill',
  'position_exit',
  'bot_started',
  'bot_stopped',
  'bot_paused',
  'run_reset',
  'error',
] as const

function num(v: unknown, digits = 2) {
  if (typeof v === 'number' && Number.isFinite(v)) return v.toFixed(digits)
  return '—'
}

function RegimeTable({ events }: { events: JournalEvent[] }) {
  const rows = events.filter((e) => e.event_type === 'regime_change')
  if (!rows.length) return <p className="muted">No regime changes in this view.</p>
  return (
    <table className="journal-regime-table">
      <thead>
        <tr>
          <th>Event time</th>
          <th>Candle time</th>
          <th>Symbol</th>
          <th>TF</th>
          <th>Trend</th>
          <th>Regime</th>
          <th>ADX</th>
          <th>ATR%</th>
          <th>Close</th>
          <th>Raw</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((e) => {
          const p = e.payload
          return (
            <tr key={e.id}>
              <td>{formatEventTime(e.created_at)}</td>
              <td>{formatCandleTime(p.candle_open_time as number)}</td>
              <td>{String(p.symbol ?? '—')}</td>
              <td>{String(p.timeframe ?? '—')}</td>
              <td>{String(p.trend ?? '—')}</td>
              <td>{String(p.regime ?? '—')}</td>
              <td>{num(p.adx)}</td>
              <td>{num(p.atr_pct)}</td>
              <td>{num(p.close)}</td>
              <td>
                <details>
                  <summary>JSON</summary>
                  <pre className="json-debug">{JSON.stringify(e.payload, null, 2)}</pre>
                </details>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function EventTable({ events }: { events: JournalEvent[] }) {
  return (
    <table className="decision-table">
      <thead>
        <tr>
          <th>Event time</th>
          <th>Type</th>
          <th>Message</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e) => (
          <tr key={e.id}>
            <td>{formatEventTime(e.created_at)}</td>
            <td><code>{e.event_type}</code></td>
            <td>{e.message}</td>
            <td>
              <details>
                <summary>Payload</summary>
                <pre className="json-debug">{JSON.stringify(e.payload, null, 2)}</pre>
                <p className="muted">id={e.id} run={e.run_id} dedupe={e.dedupe_key ?? '—'}</p>
              </details>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function Journal() {
  const { runId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const routeRunId = runId ? Number(runId) : undefined

  const [botId, setBotId] = useState<number | ''>(() => {
    const v = searchParams.get('bot_id')
    return v ? Number(v) : ''
  })
  const [eventType, setEventType] = useState(() => searchParams.get('event_type') ?? '')
  const [timeframe, setTimeframe] = useState(() => searchParams.get('timeframe') ?? '')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')

  const { data: bots = [] } = useQuery({ queryKey: ['bots'], queryFn: fetchBots })

  const params = useMemo(
    () => ({
      run_id: routeRunId,
      bot_id: botId || undefined,
      event_type: eventType || undefined,
      timeframe: timeframe || undefined,
      since: since ? new Date(since).toISOString() : undefined,
      until: until ? new Date(until).toISOString() : undefined,
      limit: 500,
    }),
    [routeRunId, botId, eventType, timeframe, since, until],
  )

  const { data: events = [], refetch, isFetching } = useQuery({
    queryKey: ['journal-events', params],
    queryFn: () => fetchJournalEvents(params),
    refetchInterval: 20_000,
  })

  const applyFiltersToUrl = () => {
    const next = new URLSearchParams()
    if (botId) next.set('bot_id', String(botId))
    if (eventType) next.set('event_type', eventType)
    if (timeframe) next.set('timeframe', timeframe)
    setSearchParams(next)
    refetch()
  }

  const exportCsv = () => {
    const header = 'event_time,event_type,message,payload\n'
    const rows = events
      .map(
        (e) =>
          `"${e.created_at}","${e.event_type}","${e.message.replace(/"/g, '""')}","${JSON.stringify(e.payload).replace(/"/g, '""')}"`,
      )
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `journal-${routeRunId ?? 'all'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const nonRegime = events.filter((e) => e.event_type !== 'regime_change')

  return (
    <div>
      <Link to="/">← Dashboard</Link>
      <div className="page-header">
        <h1>{routeRunId ? `Journal · Run #${routeRunId}` : 'Journal'}</h1>
        <button type="button" className="btn" onClick={() => refetch()} disabled={isFetching}>
          Refresh
        </button>
        <button type="button" className="btn" onClick={exportCsv}>Export CSV</button>
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
          <span>Event type</span>
          <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
            <option value="">All</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Timeframe</span>
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            <option value="">All</option>
            {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
              <option key={tf} value={tf}>{tf}</option>
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
        <button type="button" className="btn primary" onClick={applyFiltersToUrl}>Apply</button>
      </section>

      <section className="panel">
        <h2>Regime changes</h2>
        <RegimeTable events={events} />
      </section>

      <section className="panel">
        <h2>All events</h2>
        {!nonRegime.length && !events.length && (
          <p className="muted">No journal events yet.</p>
        )}
        <EventTable events={nonRegime.length ? nonRegime : events} />
      </section>
    </div>
  )
}
