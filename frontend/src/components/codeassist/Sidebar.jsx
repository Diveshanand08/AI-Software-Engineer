import { MessagesSquare, FileCode2, Bug, Database, Sparkles } from 'lucide-react'
import { cn } from '../../lib/utils'

const MODES = [
  { id: 'chat', label: 'Chat', desc: 'Ask about your codebase', icon: MessagesSquare },
  { id: 'explain', label: 'Explain', desc: 'Break down any function', icon: FileCode2 },
  { id: 'bugs', label: 'Find Bugs', desc: 'Detect issues & smells', icon: Bug },
]

export function Sidebar({ mode, onModeChange, collection, onCollectionChange, status }) {
  return (
    <aside className="glass flex w-full shrink-0 flex-col gap-6 border-r p-4 md:w-72">
      <div className="flex items-center gap-2.5 px-1 pt-1">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-amber shadow-[0_0_20px_-4px] shadow-primary/60">
          <Sparkles className="h-4.5 w-4.5 text-primary-foreground" />
        </div>
        <div className="leading-tight">
          <p className="font-mono text-sm font-semibold tracking-tight text-foreground">codeassist</p>
          <p className="text-[11px] text-muted-foreground">AI code companion</p>
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="collection" className="flex items-center gap-1.5 px-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          <Database className="h-3 w-3" />
          Collection
        </label>
        <div className="group relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-primary/70">#</span>
          <input
            id="collection"
            value={collection}
            onChange={(e) => onCollectionChange(e.target.value)}
            placeholder="test_repo"
            spellCheck={false}
            className="w-full rounded-lg border border-border bg-background/40 py-2 pl-7 pr-3 font-mono text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary/50 focus:ring-2 focus:ring-ring/40"
          />
        </div>
      </div>

      <nav className="space-y-1.5">
        <p className="px-1 pb-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Mode</p>
        {MODES.map(({ id, label, desc, icon: Icon }) => {
          const active = mode === id
          return (
            <button
              key={id}
              type="button"
              onClick={() => onModeChange(id)}
              aria-pressed={active}
              className={cn(
                'group relative flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-all',
                active ? 'border-primary/40 bg-primary/10' : 'border-transparent hover:border-border hover:bg-secondary/60',
              )}
            >
              <span className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors',
                active ? 'bg-gradient-amber text-primary-foreground shadow-[0_0_16px_-4px] shadow-primary/70' : 'bg-secondary text-muted-foreground group-hover:text-foreground',
              )}>
                <Icon className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className={cn('block font-mono text-sm font-medium', active ? 'text-foreground' : 'text-foreground/90')}>
                  {label}
                </span>
                <span className="block truncate text-[11px] text-muted-foreground">{desc}</span>
              </span>
              {active && (
                <span className="absolute right-3 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_8px] shadow-primary" />
              )}
            </button>
          )
        })}
      </nav>

      <div className="mt-auto rounded-lg border border-border bg-background/30 p-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full', status.ok ? 'bg-emerald-400/60' : 'bg-red-400/60')} />
            <span className={cn('relative inline-flex h-2 w-2 rounded-full', status.ok ? 'bg-emerald-400' : 'bg-red-400')} />
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            {status.ok ? 'backend connected' : 'backend unreachable'}
          </span>
        </div>
        <p className="mt-1.5 font-mono text-[11px] text-muted-foreground/70">localhost:8000</p>
      </div>
    </aside>
  )
}