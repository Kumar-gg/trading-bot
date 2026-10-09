import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Line, LineChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { compareRuns, fetchBots, fetchRuns } from '../api/client'

export function Compare() {
  const { data: bots = [] } = useQuery({ queryKey: ['bots'], queryFn: fetchBots })
  const [selectedBot, setSelectedBot] = useState<number | ''>('')
  const [selectedRuns, setSelectedRuns] = useState<number[]>([])
  const { data: runs = [] } = useQuery({
    queryKey: ['runs', selectedBot],
    queryFn: () => fetchRuns(Number(selectedBot)),
    enabled: !!selectedBot,
  })

  const compareMut = useMutation({ mutationFn: () => compareRuns(selectedRuns) })
  const result = compareMut.data as {
    metrics?: Array<Record<string, unknown>>
    series?: Array<{ run_id: number; label: string; points: { t: string; normalized_pct: number }[] }>
    insights?: string[]
    param_diff?: Record<string, unknown>
  } | undefined

  const chartData = (() => {
    if (!result?.series?.length) return []
    const map = new Map<string, Record<string, number | string>>()
    for (const s of result.series) {
      for (const p of s.points) {
        const row = map.get(p.t) ?? { t: p.t }
        row[`run_${s.run_id}`] = p.normalized_pct
        map.set(p.t, row)
      }
    }
    return Array.from(map.values()).sort((a, b) => String(a.t).localeCompare(String(b.t)))
  })()

  const toggleRun = (runId: number) => {
    setSelectedRuns((prev) =>
      prev.includes(runId) ? prev.filter((x) => x !== runId) : [...prev, runId]
    )
  }

  return (
    <div>
      <h1>Compare runs</h1>
      <section className="panel">
        <label className="field">
          <span>Bot</span>
          <select value={selectedBot} onChange={(e) => { setSelectedBot(e.target.value ? Number(e.target.value) : ''); setSelectedRuns([]) }}>
            <option value="">Select bot</option>
            {bots.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
        <div className="run-picks">
          {runs.map((r) => (
            <label key={r.id} className="chip">
              <input type="checkbox" checked={selectedRuns.includes(r.id)} onChange={() => toggleRun(r.id)} />
              Run #{r.id} ({r.template_id})
            </label>
          ))}
        </div>
        <button className="btn primary" disabled={selectedRuns.length < 2} onClick={() => compareMut.mutate()}>
          Compare selected
        </button>
      </section>

      {result?.metrics && (
        <section className="panel">
          <h2>Metrics</h2>
          <table>
            <thead>
              <tr>
                <th>Run</th><th>Return %</th><th>Trades</th><th>Win rate</th><th>Max DD</th><th>Profit factor</th>
              </tr>
            </thead>
            <tbody>
              {result.metrics.map((m) => (
                <tr key={String(m.run_id)}>
                  <td>{String(m.run_id)}</td>
                  <td>{Number(m.return_pct).toFixed(2)}</td>
                  <td>{String(m.trade_count)}</td>
                  <td>{Number(m.win_rate).toFixed(1)}</td>
                  <td>{Number(m.max_drawdown_pct).toFixed(2)}</td>
                  <td>{m.profit_factor == null ? '—' : Number(m.profit_factor).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {chartData.length > 0 && (
        <section className="panel">
          <h2>Normalized equity (%)</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <XAxis dataKey="t" hide />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              {result?.series?.map((s) => (
                <Line key={s.run_id} type="monotone" dataKey={`run_${s.run_id}`} name={s.label} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}

      {result?.insights && (
        <section className="panel">
          <h2>Insights</h2>
          <ul>{result.insights.map((i) => <li key={i}>{i}</li>)}</ul>
          {result.param_diff && Object.keys(result.param_diff).length > 0 && (
            <>
              <h3>Parameter differences (first two runs)</h3>
              <pre>{JSON.stringify(result.param_diff, null, 2)}</pre>
            </>
          )}
        </section>
      )}
    </div>
  )
}
