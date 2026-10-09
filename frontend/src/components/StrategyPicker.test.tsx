import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { StrategyPicker } from './StrategyPicker'
import type { Strategy } from '../api/client'

const strategies: Strategy[] = [
  {
    id: 'ema_trend',
    name: 'EMA Trend',
    description: 'd',
    category: 'trend',
    supported_timeframes: ['5m'],
    params_schema: {},
  },
  {
    id: 'bb_mean_revert',
    name: 'BB Mean Revert',
    description: 'd',
    category: 'mean_reversion',
    supported_timeframes: ['5m'],
    params_schema: {},
  },
]

describe('StrategyPicker', () => {
  it('filters strategies by category', async () => {
    const user = userEvent.setup()
    render(<StrategyPicker strategies={strategies} value="ema_trend" onChange={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /mean reversion/i }))
    expect(screen.queryByRole('option', { name: 'EMA Trend' })).toBeNull()
    expect(screen.getByRole('option', { name: 'BB Mean Revert' })).toBeInTheDocument()
  })
})
