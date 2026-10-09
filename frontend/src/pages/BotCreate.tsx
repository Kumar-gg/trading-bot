import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { createBot, fetchStrategies } from '../api/client'
import { BotParamForm } from '../components/BotParamForm'
import { StrategyPicker } from '../components/StrategyPicker'

export function BotCreate() {
  const nav = useNavigate()
  const { data: strategies = [] } = useQuery({ queryKey: ['strategies'], queryFn: fetchStrategies })
  const [name, setName] = useState('My Bot')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState('5m')
  const [templateId, setTemplateId] = useState('ema_trend')
  const [params, setParams] = useState<Record<string, unknown>>({})

  const strategy = strategies.find((s) => s.id === templateId)
  const schema = useMemo(() => strategy?.params_schema ?? {}, [strategy])

  useEffect(() => {
    if (!strategy) return
    const props = (strategy.params_schema as { properties?: Record<string, { default?: unknown }> }).properties ?? {}
    const defaults: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(props)) {
      if (v.default !== undefined) defaults[k] = v.default
    }
    setParams(defaults)
  }, [strategy])

  const mut = useMutation({
    mutationFn: () => createBot({ name, symbol, timeframe, template_id: templateId, params }),
    onSuccess: (bot) => nav(`/bots/${bot.id}`),
  })

  return (
    <div>
      <h1>Create bot</h1>
      <section className="panel">
        <label className="field" htmlFor="bot-name"><span>Name</span><input id="bot-name" value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field"><span>Symbol</span><input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} /></label>
        <label className="field">
          <span>Timeframe</span>
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            {(strategy?.supported_timeframes ?? ['5m']).map((tf) => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </label>
        <StrategyPicker strategies={strategies} value={templateId} onChange={setTemplateId} />
        <p className="muted">{strategy?.description}{strategy?.category ? ` · ${strategy.category}` : ''}</p>
        <BotParamForm schema={schema as never} values={params} onChange={setParams} />
        <button className="btn primary" onClick={() => mut.mutate()}>Create</button>
      </section>
    </div>
  )
}
