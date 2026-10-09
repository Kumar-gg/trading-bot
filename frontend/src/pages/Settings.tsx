import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function Settings() {
  const { data } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await api.get('/settings')).data as {
      fee_bps: number
      slippage_bps: number
      market_connected: boolean
      rest_ok: boolean
      ws_connected: boolean
      last_error: string | null
    },
    refetchInterval: 10_000,
  })

  return (
    <div>
      <h1>Settings</h1>
      <section className="panel">
        <p>Fee (bps): {data?.fee_bps ?? '—'}</p>
        <p>Slippage (bps): {data?.slippage_bps ?? '—'}</p>
        <p>
          Binance prices (REST):{' '}
          <span className={data?.rest_ok ? 'pos' : 'neg'}>{data?.rest_ok ? 'OK' : 'Unavailable'}</span>
        </p>
        <p>
          Live candles (WebSocket):{' '}
          <span className={data?.ws_connected ? 'pos' : 'muted'}>
            {data?.ws_connected ? 'Connected' : data?.rest_ok ? 'Waiting (start a bot)' : '—'}
          </span>
        </p>
        {data?.last_error && (
          <p className="neg" style={{ fontSize: '0.9rem' }}>Last error: {data.last_error}</p>
        )}
        <p className="muted">Paper trading uses simulated fills; no Binance API keys needed.</p>
      </section>
    </div>
  )
}
