import { useMemo, useState } from 'react'
import type { Strategy } from '../api/client'

const CATEGORY_LABELS: Record<string, string> = {
  all: 'All',
  trend: 'Trend',
  mean_reversion: 'Mean reversion',
  breakout: 'Breakout',
  volatility: 'Volatility',
}

interface Props {
  strategies: Strategy[]
  value: string
  onChange: (id: string) => void
}

export function StrategyPicker({ strategies, value, onChange }: Props) {
  const categories = useMemo(() => {
    const set = new Set(strategies.map((s) => s.category))
    return ['all', ...Array.from(set).sort()]
  }, [strategies])
  const [filter, setFilter] = useState('all')

  const filtered = useMemo(
    () => (filter === 'all' ? strategies : strategies.filter((s) => s.category === filter)),
    [strategies, filter],
  )

  const grouped = useMemo(() => {
    const map = new Map<string, Strategy[]>()
    for (const s of filtered) {
      const list = map.get(s.category) ?? []
      list.push(s)
      map.set(s.category, list)
    }
    return map
  }, [filtered])

  return (
    <div className="strategy-picker">
      <div className="strategy-filter">
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            className={`chip-btn ${filter === c ? 'active' : ''}`}
            onClick={() => setFilter(c)}
          >
            {CATEGORY_LABELS[c] ?? c}
          </button>
        ))}
      </div>
      <label className="field">
        <span>Strategy</span>
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {Array.from(grouped.entries()).map(([cat, list]) => (
            <optgroup key={cat} label={CATEGORY_LABELS[cat] ?? cat}>
              {list.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
    </div>
  )
}
