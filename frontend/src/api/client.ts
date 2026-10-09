import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export type BotStatus = 'idle' | 'running' | 'paused'
export type BotHealthStatus = 'idle' | 'active' | 'stale' | 'error'
export type DecisionType = 'BUY' | 'SELL' | 'HOLD' | 'REJECTED'

export interface Bot {
  id: number
  name: string
  status: BotStatus
  symbol: string
  timeframe: string
  template_id: string
  params: Record<string, unknown>
  initial_capital: number
  current_run_id: number | null
  created_at: string
  equity?: number | null
  return_pct?: number | null
  position_qty?: number | null
  health_status?: BotHealthStatus
  last_evaluation_at?: string | null
  last_market_data_at?: string | null
  latest_decision?: DecisionType | null
  latest_decision_reason?: string | null
  last_eval_error?: string | null
}

export interface DecisionLog {
  id: number
  bot_id: number
  run_id: number
  evaluated_at: string
  candle_open_time: number | null
  symbol_price: number | null
  btc_price: number | null
  market_data_age_sec: number | null
  indicators: Record<string, unknown>
  entry_conditions: Array<{ name: string; passed: boolean; detail: string; kind?: string }>
  exit_conditions: Array<{ name: string; passed: boolean; detail: string; kind?: string }>
  decision: DecisionType
  reason: string
  rejection_source: string | null
  rejection_detail: string | null
}

export interface Strategy {
  id: string
  name: string
  description: string
  category: string
  supported_timeframes: string[]
  params_schema: Record<string, unknown>
}

export interface JournalEvent {
  id: number
  run_id: number
  bot_id?: number | null
  event_type: string
  message: string
  payload: Record<string, unknown>
  dedupe_key?: string | null
  created_at: string
}

export interface RunSummary {
  id: number
  started_at: string
  ended_at: string | null
  starting_equity: number
  template_id: string
  params_snapshot: Record<string, unknown>
}

export async function fetchBots() {
  const { data } = await api.get<Bot[]>('/bots')
  return data
}

export async function fetchBot(id: number) {
  const { data } = await api.get<Bot>(`/bots/${id}`)
  return data
}

export async function createBot(payload: Partial<Bot> & { name: string }) {
  const { data } = await api.post<Bot>('/bots', payload)
  return data
}

export async function updateBot(id: number, payload: Partial<Bot>) {
  const { data } = await api.patch<Bot>(`/bots/${id}`, payload)
  return data
}

export async function botAction(id: number, action: 'start' | 'pause' | 'stop' | 'reset') {
  const { data } = await api.post<Bot>(`/bots/${id}/${action}`)
  return data
}

export async function fetchStrategies() {
  const { data } = await api.get<Strategy[]>('/strategies')
  return data
}

export async function fetchRuns(botId: number) {
  const { data } = await api.get<RunSummary[]>(`/bots/${botId}/runs`)
  return data
}

export async function fetchJournal(runId: number) {
  const { data } = await api.get<JournalEvent[]>(`/bots/runs/${runId}/journal`)
  return data
}

export async function fetchJournalEvents(params: {
  run_id?: number
  bot_id?: number
  event_type?: string
  timeframe?: string
  since?: string
  until?: string
  limit?: number
} = {}) {
  const { data } = await api.get<JournalEvent[]>('/journal', { params })
  return data
}

export async function fetchEquityCurve(runId: number) {
  const { data } = await api.get<{ t: string; equity: number }[]>(`/bots/runs/${runId}/equity-curve`)
  return data
}

export async function compareRuns(runIds: number[]) {
  const { data } = await api.post('/compare', { run_ids: runIds })
  return data
}

export async function fetchDecisions(params: {
  bot_id?: number
  decision?: DecisionType
  since?: string
  until?: string
  limit?: number
} = {}) {
  const { data } = await api.get<DecisionLog[]>('/decisions', { params })
  return data
}
