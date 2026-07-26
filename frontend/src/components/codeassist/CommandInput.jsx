import { useRef, useState } from 'react'
import { CornerDownLeft, Play } from 'lucide-react'

const PLACEHOLDER = {
  chat: 'Ask anything about your codebase…',
  explain: 'Name a function or class to explain…',
  bugs: 'Enter a file path to audit…',
}

export function CommandInput({ value, onChange, onSubmit, mode, disabled }) {
  const [composing, setComposing] = useState(false)
  const inputRef = useRef(null)

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !composing && e.nativeEvent.isComposing !== true && e.keyCode !== 229) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    if (!value.trim() || disabled) return
    onSubmit()
    inputRef.current?.focus()
  }

  return (
    <div className="px-4 pb-5 pt-2 md:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="group relative flex items-end gap-2 rounded-xl border border-border bg-card/70 p-2 backdrop-blur-md transition-colors focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-ring/30">
          <span className="select-none pl-2 pb-2.5 font-mono text-base font-semibold text-primary">$</span>
          <textarea
            ref={inputRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setComposing(true)}
            onCompositionEnd={() => setComposing(false)}
            placeholder={PLACEHOLDER[mode]}
            spellCheck={false}
            disabled={disabled}
            className="max-h-40 min-h-9 flex-1 resize-none bg-transparent py-2 font-mono text-sm text-foreground outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || disabled}
            className="flex shrink-0 items-center gap-1.5 rounded-lg bg-gradient-amber px-3.5 py-2 font-mono text-sm font-semibold text-primary-foreground shadow-[0_0_20px_-6px] shadow-primary/70 transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            Run
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between px-1">
          <p className="font-mono text-[11px] text-muted-foreground/70">RAG-grounded · responses cite indexed sources</p>
          <p className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground/70">
            <CornerDownLeft className="h-3 w-3" />
            to run · shift + enter for newline
          </p>
        </div>
      </div>
    </div>
  )
}