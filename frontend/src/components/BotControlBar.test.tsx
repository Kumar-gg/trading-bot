import { render, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BotControlBar } from './BotControlBar'

describe('BotControlBar', () => {
  it('highlights running mode and disables start', () => {
    const { container } = render(<BotControlBar status="running" busy={false} onAction={vi.fn()} />)
    const root = container.firstElementChild as HTMLElement
    expect(root.querySelector('.bot-state-step.is-current')).toHaveTextContent('Running')
    const actions = root.querySelector('.bot-control-actions') as HTMLElement
    expect(within(actions).getByRole('button', { name: /^start$/i })).toBeDisabled()
    expect(within(actions).getByRole('button', { name: /^pause$/i })).toBeEnabled()
  })

  it('calls onAction when pause clicked', async () => {
    const user = userEvent.setup()
    const onAction = vi.fn()
    const { container } = render(<BotControlBar status="running" busy={false} onAction={onAction} />)
    const actions = container.querySelector('.bot-control-actions') as HTMLElement
    await user.click(within(actions).getByRole('button', { name: /^pause$/i }))
    expect(onAction).toHaveBeenCalledWith('pause')
  })

  it('idle enables only start', () => {
    const { container } = render(<BotControlBar status="idle" busy={false} onAction={vi.fn()} />)
    const root = container.firstElementChild as HTMLElement
    expect(root.querySelector('.bot-state-step.is-current')).toHaveTextContent('Stopped')
    const actions = root.querySelector('.bot-control-actions') as HTMLElement
    expect(within(actions).getByRole('button', { name: /^start$/i })).toBeEnabled()
    expect(within(actions).getByRole('button', { name: /^pause$/i })).toBeDisabled()
    expect(within(actions).getByRole('button', { name: /^stop$/i })).toBeDisabled()
  })
})
