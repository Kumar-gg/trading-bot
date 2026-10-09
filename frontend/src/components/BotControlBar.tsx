import type { BotStatus } from '../api/client'

type Action = 'start' | 'pause' | 'stop' | 'reset'

interface Props {
  status: BotStatus
  busy: boolean
  onAction: (action: Action) => void
}

const STEPS: { id: BotStatus; label: string; hint: string }[] = [
  { id: 'idle', label: 'Stopped', hint: 'Not trading — press Start to begin' },
  { id: 'running', label: 'Running', hint: 'Actively paper trading on new candles' },
  { id: 'paused', label: 'Paused', hint: 'Trading halted — resume with Start or end with Stop' },
]

function IconPlay() {
  return (
    <svg className="ctrl-icon" viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M8 5v14l11-7z" />
    </svg>
  )
}

function IconPause() {
  return (
    <svg className="ctrl-icon" viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M6 5h4v14H6zm8 0h4v14h-4z" />
    </svg>
  )
}

function IconStop() {
  return (
    <svg className="ctrl-icon" viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M6 6h12v12H6z" />
    </svg>
  )
}

function IconReset() {
  return (
    <svg className="ctrl-icon" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M12 6V3L8 7l4 4V8c2.76 0 5 2.24 5 5 0 1.02-.31 1.96-.84 2.75l1.46 1.46A6.96 6.96 0 0019 13c0-3.87-3.13-7-7-7zm0 12c-2.76 0-5-2.24-5-5 0-1.02.31-1.96.84-2.75L6.38 9.79A6.96 6.96 0 005 13c0 3.87 3.13 7 7 7v3l4-4-4-4v3z"
      />
    </svg>
  )
}

export function BotControlBar({ status, busy, onAction }: Props) {
  const canStart = status === 'idle' || status === 'paused'
  const canPause = status === 'running'
  const canStop = status === 'running' || status === 'paused'
  const current = STEPS.find((s) => s.id === status) ?? STEPS[0]

  return (
    <div className="bot-control-bar">
      <div className="bot-state-track" role="status" aria-live="polite">
        <span className="bot-state-track-label">Current mode</span>
        <div className="bot-state-steps">
          {STEPS.map((step) => (
            <div
              key={step.id}
              className={`bot-state-step bot-state-${step.id} ${status === step.id ? 'is-current' : ''}`}
              title={step.hint}
            >
              <span className="bot-state-dot" aria-hidden />
              <span>{step.label}</span>
            </div>
          ))}
        </div>
        <p className="bot-state-hint muted">{current.hint}</p>
      </div>

      <div className="bot-control-actions">
        <button
          type="button"
          className="btn ctrl start"
          disabled={busy || !canStart}
          title={canStart ? 'Start or resume paper trading' : 'Already running'}
          onClick={() => onAction('start')}
        >
          <IconPlay />
          Start
        </button>
        <button
          type="button"
          className="btn ctrl pause"
          disabled={busy || !canPause}
          title={canPause ? 'Pause trading (keeps this run open)' : 'Only available while running'}
          onClick={() => onAction('pause')}
        >
          <IconPause />
          Pause
        </button>
        <button
          type="button"
          className="btn ctrl stop"
          disabled={busy || !canStop}
          title={canStop ? 'Stop and archive this run' : 'Already stopped'}
          onClick={() => onAction('stop')}
        >
          <IconStop />
          Stop
        </button>
      </div>

      <div className="bot-control-reset">
        <button
          type="button"
          className="btn ctrl reset warn"
          disabled={busy}
          title="Close current run and start a fresh paper balance (history kept for Compare)"
          onClick={() => onAction('reset')}
        >
          <IconReset />
          Reset journey
        </button>
      </div>
    </div>
  )
}
