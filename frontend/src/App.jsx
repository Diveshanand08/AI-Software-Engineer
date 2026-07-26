import { useEffect, useState } from 'react'
import { Command, GitBranch, Settings2 } from 'lucide-react'
import { Sidebar } from './components/codeassist/Sidebar.jsx'
import { ChatPanel } from './components/codeassist/ChatPanel.jsx'
import { CommandInput } from './components/codeassist/CommandInput.jsx'

const API_BASE = 'http://localhost:8000'

const MODE_TITLE = { chat: 'Chat', explain: 'Explain', bugs: 'Find Bugs' }

export default function App() {
  const [mode, setMode] = useState('chat')
  const [collection, setCollection] = useState('test_repo')
  const [messagesByMode, setMessagesByMode] = useState({ chat: [], explain: [], bugs: [] })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [status, setStatus] = useState({ ok: false })

  const messages = messagesByMode[mode]

  // ping the backend once on load so the sidebar status is real, not decorative
  useEffect(() => {
    fetch(`${API_BASE}/`)
      .then((res) => setStatus({ ok: res.ok }))
      .catch(() => setStatus({ ok: false }))
  }, [])

  useEffect(() => {
    let timer
    if (loading) {
      setElapsed(0)
      timer = setInterval(() => setElapsed((e) => e + 1), 1000)
    }
    return () => clearInterval(timer)
  }, [loading])

  function appendMessage(m) {
    setMessagesByMode((prev) => ({ ...prev, [mode]: [...prev[mode], m] }))
  }

  async function send(text) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    appendMessage({ id: crypto.randomUUID(), role: 'user', content: trimmed })
    setInput('')
    setLoading(true)

    try {
      let res, data, replyText

      if (mode === 'bugs') {
        res = await fetch(`${API_BASE}/bugs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_path: trimmed }),
        })
        data = await res.json()
        replyText = data.analysis || data.detail || 'No response.'
      } else {
        const endpoint = mode === 'explain' ? '/explain' : '/ask'
        const body = mode === 'explain'
          ? { collection, target: trimmed }
          : { collection, question: trimmed }
        res = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        data = await res.json()
        replyText = data.answer || data.detail || 'No response.'
      }

      appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: replyText })
    } catch (e) {
      appendMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${e.message}\n\nIs the FastAPI backend running on ${API_BASE}?`,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-grid relative flex h-screen w-full overflow-hidden bg-background">
      <div className="glow-amber pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full blur-3xl" />
      <div className="glow-amber pointer-events-none absolute -bottom-40 right-10 h-96 w-96 rounded-full opacity-60 blur-3xl" />

      <Sidebar
        mode={mode}
        onModeChange={setMode}
        collection={collection}
        onCollectionChange={setCollection}
        status={status}
      />

      <main className="relative z-10 flex min-w-0 flex-1 flex-col">
        <header className="glass flex items-center justify-between border-b px-4 py-3 md:px-8">
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-sm font-semibold tracking-tight text-foreground">
              {MODE_TITLE[mode]}
            </h1>
            <span className="hidden items-center gap-1.5 rounded-full border border-border bg-secondary/50 px-2.5 py-1 font-mono text-[11px] text-muted-foreground sm:flex">
              <span className="text-primary/70">#</span>
              {collection || 'no-collection'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <button type="button" className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:text-foreground">
              <Command className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">K</span>
            </button>
            <button type="button" aria-label="Repository" className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-secondary/40 text-muted-foreground transition-colors hover:text-foreground">
              <GitBranch className="h-4 w-4" />
            </button>
            <button type="button" aria-label="Settings" className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-secondary/40 text-muted-foreground transition-colors hover:text-foreground">
              <Settings2 className="h-4 w-4" />
            </button>
          </div>
        </header>

        <ChatPanel messages={messages} mode={mode} onExample={send} loading={loading} elapsed={elapsed} />

        <CommandInput value={input} onChange={setInput} onSubmit={() => send(input)} mode={mode} disabled={loading} />
      </main>
    </div>
  )
}