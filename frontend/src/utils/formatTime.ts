function tzLabel(): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const offsetMin = -new Date().getTimezoneOffset()
  const sign = offsetMin >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMin)
  const hh = String(Math.floor(abs / 60)).padStart(2, '0')
  const mm = String(abs % 60).padStart(2, '0')
  return `${tz} (UTC${sign}${hh}:${mm})`
}

export function formatEventTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const formatted = new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(d)
  return `${formatted} · ${tzLabel()}`
}

export function formatCandleTime(ms: number | null | undefined): string {
  if (!ms) return '—'
  return formatEventTime(new Date(ms).toISOString())
}

export const TZ_LABEL = tzLabel()
