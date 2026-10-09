import { useMemo } from 'react'

type JsonSchema = {
  properties?: Record<string, { type?: string; title?: string; minimum?: number; maximum?: number; default?: unknown; anyOf?: { type?: string }[] }>
  required?: string[]
}

interface Props {
  schema: JsonSchema
  values: Record<string, unknown>
  onChange: (next: Record<string, unknown>) => void
}

export function BotParamForm({ schema, values, onChange }: Props) {
  const fields = useMemo(() => {
    const props = schema.properties ?? {}
    return Object.entries(props)
  }, [schema])

  return (
    <div className="param-form">
      {fields.map(([key, field]) => {
        const val = values[key] ?? field.default ?? ''
        const label = field.title ?? key
        const fieldType = field.type ?? field.anyOf?.find((t) => t.type)?.type
        const isInt = fieldType === 'integer'
        const isBool = fieldType === 'boolean'
        if (isBool) {
          return (
            <label key={key} className="field checkbox">
              <input
                type="checkbox"
                checked={Boolean(val)}
                onChange={(e) => onChange({ ...values, [key]: e.target.checked })}
              />
              <span>{label}</span>
            </label>
          )
        }
        return (
          <label key={key} className="field">
            <span>{label}</span>
            <input
              type="number"
              step={isInt ? 1 : 0.1}
              min={field.minimum}
              max={field.maximum}
              value={val as number | string}
              onChange={(e) => {
                const raw = e.target.value
                const parsed = isInt ? parseInt(raw, 10) : parseFloat(raw)
                onChange({ ...values, [key]: Number.isNaN(parsed) ? raw : parsed })
              }}
            />
          </label>
        )
      })}
    </div>
  )
}
