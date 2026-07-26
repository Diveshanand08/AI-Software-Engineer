import { useEffect, useRef } from 'react'
import { User, Terminal, MessagesSquare, FileCode2, Bug } from 'lucide-react'
import { cn } from '../../lib/utils'

const EMPTY_STATE = {
  chat: {
    icon: MessagesSquare,
    title: 'Chat with your codebase',
    desc: 'Ask questions in natural language. CodeAssist retrieves the most relevant snippets from your indexed collection and answers with grounded context.',
    examples: ['How does chunk_python_file work?', 'What does the retriever return?', 'Explain the indexing pipeline'],
  },
  explain: {
    icon: FileCode2,
    title: 'Explain any function',
    desc: 'Enter a function or class name. Get a structured breakdown: purpose, parameters, logic flow, and edge cases.',
    examples: ['chunk_python_file', 'run_code_in_sandbox', 'clone_repo'],
  },
  bugs: {
    icon: Bug,
    title: 'Find bugs & code smells',
    desc: 'Point CodeAssist at a file path. It runs static analysis plus LLM reasoning, separating real issues from style noise.',
    examples: ['indexer.py', 'sandbox.py', 'retriever.py'],
  },
}

function EmptyState({ mode, onExample }) {
  const { icon: Icon, title, desc, examples } = EMPTY_STATE[mode]
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="relative mb-7 flex items-center justify-center">
        <div className="glow-amber absolute h-48 w-48 rounded-full blur-xl" />
        <div className="relative flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl border border-glass-border bg-glass backdrop-blur-md">
          <span className="pointer-events-none absolute inset-0 bg-gradient-amber opacity-15" />
          <Icon className="relative h-11 w-11 text-primary drop-shadow-[0_0_12px_var(--primary)]" strokeWidth={1.5} />
        </div>
      </div>
      <h2 className="text-balance font-mono text-xl font-semibold tracking-tight text-foreground">{title}</h2>
      <p className="mt-3 max-w-md text-pretty text-sm leading-relaxed text-muted-foreground">{desc}</p>
      <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => onExample(ex)}
            className="rounded-full border border-border bg-secondary/50 px-3.5 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-foreground"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex w-full gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border',
        isUser ? 'border-border bg-secondary text-foreground' : 'border-primary/30 bg-gradient-amber text-primary-foreground shadow-[0_0_18px_-6px] shadow-primary/70',
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Terminal className="h-4 w-4" />}
      </div>
      <div className={cn(
        'max-w-[80%] rounded-2xl border px-4 py-3 text-sm leading-relaxed',
        isUser ? 'rounded-tr-sm border-border bg-secondary/70 text-foreground' : 'rounded-tl-sm border-glass-border bg-glass font-mono text-foreground/90 backdrop-blur-sm',
      )}>
        <p className="whitespace-pre-wrap text-pretty">{message.content}</p>
      </div>
    </div>
  )
}

function ThinkingIndicator({ elapsed }) {
  return (
    <div className="flex w-full gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/30 bg-gradient-amber text-primary-foreground shadow-[0_0_18px_-6px] shadow-primary/70">
        <Terminal className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-glass-border bg-glass px-4 py-3 font-mono text-xs text-muted-foreground backdrop-blur-sm">
        <span className="flex gap-1">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:0.2s]" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:0.4s]" />
        </span>
        processing locally ({elapsed}s) — local models can take a couple of minutes
      </div>
    </div>
  )
}

export function ChatPanel({ messages, mode, onExample, loading, elapsed }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 overflow-hidden">
        <EmptyState mode={mode} onExample={onExample} />
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 md:px-8">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {loading && <ThinkingIndicator elapsed={elapsed} />}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}