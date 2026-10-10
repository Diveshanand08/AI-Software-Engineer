import { useEffect, useState } from 'react'

export function ModelPicker({ apiBase, value, onChange }) {
  const [options, setOptions] = useState([{ id: 'ollama', label: 'Local (phi3)' }])

 useEffect(() => {
  fetch(`${apiBase}/providers`)
    .then((r) => r.json())
    .then((list) => {
      if (!Array.isArray(list) || list.length === 0) return  // ignore bad responses
      setOptions(list)
      if (!list.some((o) => o.id === value)) onChange(list[0].id)
    })
    .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [apiBase])

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Model"
      className="h-8 rounded-lg border border-border bg-secondary/40 px-2 font-mono text-xs text-foreground outline-none transition-colors hover:bg-secondary/70 focus:border-primary/50"
    >
      {options.map((o) => (
        <option key={o.id} value={o.id} className="bg-[#1e1f20]">
          {o.label}
        </option>
      ))}
    </select>
  )
}