import { useEffect, useState, useCallback, useRef } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { Command, GitBranch, Settings2, Menu, LogOut, Plus } from 'lucide-react'
import { Sidebar } from './components/codeassist/Sidebar.jsx'
import { ChatPanel } from './components/codeassist/ChatPanel.jsx'
import { CommandInput } from './components/codeassist/CommandInput.jsx'
import { ModelPicker } from './components/codeassist/modelpicker.jsx'
import { useAuth } from './lib/useAuth.js'
const API_BASE = 'http://localhost:8000'
const MODE_TITLE = { chat: 'Chat', explain: 'Explain', bugs: 'Find Bugs', agent: 'Auto-Coder Agent' }

export default function App() {
  const { user, displayName, login, logout } = useAuth()
  const [mode, setMode] = useState('chat')
  const [collection, setCollection] = useState('test_repo')
  
  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const [activeSessionId, setActiveSessionId] = useState(null)
  const skipSessionLoadRef = useRef(false)
  const [messages, setMessages] = useState([])
  const [historyList, setHistoryList] = useState([]) 

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [status, setStatus] = useState({ ok: false })
  const [repoUrl, setRepoUrl] = useState('')
  const [isIndexing, setIsIndexing] = useState(false)
  const [provider, setProvider] = useState(() => localStorage.getItem('provider') || 'ollama')

function handleProviderChange(p) {
  setProvider(p)
  localStorage.setItem('provider', p)
}

  const fetchHistory = useCallback(async () => {
    try {
      const emailQuery = user?.email ? `?user_email=${encodeURIComponent(user.email)}` : ''
      const res = await fetch(`${API_BASE}/sessions${emailQuery}`)
      if (res.ok) {
        const data = await res.json()
        setHistoryList(data)
      }
    } catch (e) {
      console.error("Failed to fetch history:", e)
    }
  }, [user?.email])

  useEffect(() => {
    setActiveSessionId(null)
    setMessages([])
    fetchHistory()
  }, [user?.email, fetchHistory])

  useEffect(() => {
    fetch(`${API_BASE}/`)
      .then((res) => setStatus({ ok: res.ok }))
      .catch(() => setStatus({ ok: false }))
  }, [])

  useEffect(() => {
    if (skipSessionLoadRef.current) {
      skipSessionLoadRef.current = false
      return
    }
    if (!activeSessionId) {
      setMessages([]) 
      return
    }
    const loadPastChat = async () => {
      try {
        const res = await fetch(`${API_BASE}/sessions/${activeSessionId}`)
        if (res.ok) {
          const data = await res.json()
          const formatted = data.map(m => ({ ...m, id: crypto.randomUUID() }))
          setMessages(formatted)
        }
      } catch (e) {
        console.error("Failed to load session:", e)
      }
    }
    loadPastChat()
  }, [activeSessionId])

  useEffect(() => {
    let timer
    if (loading) {
      setElapsed(0)
      timer = setInterval(() => setElapsed((e) => e + 1), 1000)
    }
    return () => clearInterval(timer)
  }, [loading])

  function appendMessage(m) {
    setMessages((prev) => [...prev, m])
  }

  async function handleImport() {
    if (!repoUrl.trim() || !collection.trim() || isIndexing) return
    setIsIndexing(true)
    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: collection, repo_url: repoUrl }),
      })
      const data = await res.json()
      alert(data.message)
      setRepoUrl('')
    } catch (e) {
      alert(`Error starting import: ${e.message}`)
    } finally {
      setIsIndexing(false)
    }
  }

  async function handleDeleteSession(id) {
    try {
      await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' })
      if (activeSessionId === id) {
        setActiveSessionId(null)
        setMessages([])
      }
      fetchHistory()
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  async function send(text) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    appendMessage({ id: crypto.randomUUID(), role: 'user', content: trimmed })
    setInput('')
    setLoading(true)


    try {
      if (mode === 'bugs') {
        const res = await fetch(`${API_BASE}/bugs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_path: trimmed }),
        })
        const data = await res.json()
        appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: data.analysis || 'No response.' })
      } else {
        const endpoint = mode === 'explain' ? '/explain' : '/ask'
        const body = {
          collection,
          question: trimmed,
          target: trimmed,
          session_id: activeSessionId,
          provider,
          user_email: user?.email || '',
        }
        
        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })

        if (!res.ok) {
          const errText = await res.text()
          throw new Error(errText || `Server error: ${res.status}`)
        }

        const msgId = crypto.randomUUID()
        appendMessage({ id: msgId, role: 'assistant', content: '' })

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          
          const sessionMatch = buffer.match(/__SESSION_ID__:(.+?)\n\n/)
          if (sessionMatch) {
            skipSessionLoadRef.current = true
            setActiveSessionId(sessionMatch[1])
            buffer = buffer.replace(sessionMatch[0], '')
            fetchHistory() 
          }

          if (buffer.includes('__SESSION_ID') && !sessionMatch) {
            continue 
          }
          
          if (buffer.length > 0) {
            const currentText = buffer
            setMessages(prev => prev.map(msg => 
              msg.id === msgId ? { ...msg, content: msg.content + currentText } : msg
            ))
            buffer = '' 
          }
        }
      }
    } catch (e) {
      appendMessage({ id: crypto.randomUUID(), role: 'assistant', content: `Error: ${e.message}` })
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = useCallback(() => {
    setActiveSessionId(null)
    setMessages([])
    setIsSidebarOpen(false)
  }, [])

  return (
    <div className="bg-grid fixed inset-0 flex overflow-hidden bg-background">
      <div className="glow-amber pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full blur-3xl" />
      <div className="glow-amber pointer-events-none absolute -bottom-40 right-10 h-96 w-96 rounded-full opacity-60 blur-3xl" />

      {/* Floating Sidebar Overlay */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        mode={mode}
        onModeChange={setMode}
        collection={collection}
        onCollectionChange={setCollection}
        status={status}
        repoUrl={repoUrl}
        onRepoUrlChange={setRepoUrl}
        onImport={handleImport}
        isIndexing={isIndexing}
        historyList={historyList}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id)
          setIsSidebarOpen(false)
        }}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
      />

      {/* Ensure the main container does NOT scroll by adding relative, h-full, and overflow-hidden */}
      <main className="relative z-10 flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        
        {/* Header - Stays fixed at top */}
        <header className="glass shrink-0 flex items-center justify-between border-b px-4 py-3 md:px-8">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="mr-2 flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="font-mono text-sm font-semibold tracking-tight text-foreground">
              {MODE_TITLE[mode]}
            </h1>
            <span className="hidden items-center gap-1.5 rounded-full border border-border bg-secondary/50 px-2.5 py-1 font-mono text-[11px] text-muted-foreground sm:flex">
              <span className="text-primary/70">#</span>
              {collection || 'no-collection'}
            </span>

            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1 font-mono text-xs text-muted-foreground transition-colors hover:bg-secondary/70 hover:text-foreground active:scale-95"
              title="Start a new chat"
            >
              <Plus className="h-3.5 w-3.5 text-blue-400" />
              <span className="hidden sm:inline">New Chat</span>
            </button>
          </div>
          <div className="flex items-center gap-1.5">
            <ModelPicker apiBase={API_BASE} value={provider} onChange={handleProviderChange} />
  
            <button type="button" aria-label="Repository" className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-secondary/40 text-muted-foreground transition-colors hover:text-foreground">
              <GitBranch className="h-4 w-4" />
            </button>
            <button type="button" aria-label="Settings" className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-secondary/40 text-muted-foreground transition-colors hover:text-foreground">
              <Settings2 className="h-4 w-4" />
            </button>

            {/* Auth section */}
            {user ? (
              <div className="flex items-center gap-2 ml-1">
                {user.picture ? (
                  <img src={user.picture} alt={displayName} className="h-7 w-7 rounded-full ring-1 ring-white/20" />
                ) : (
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 font-mono text-xs font-bold text-white">
                    {displayName[0].toUpperCase()}
                  </div>
                )}
                <button
                  onClick={logout}
                  title="Sign out"
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-white/10 hover:text-white transition-colors"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <div className="ml-1 scale-75 origin-right">
                <GoogleLogin
                  onSuccess={login}
                  onError={() => console.error('Google login failed')}
                  shape="pill"
                  size="medium"
                  theme="filled_black"
                  text="signin"
                />
              </div>
            )}
          </div>
        </header>

        {/* 
          THE FIX: 
          We separate the ChatPanel and the CommandInput completely.
          ChatPanel takes up all available vertical space (flex-1).
          CommandInput is absolutely positioned relative to this specific wrapper. 
        */}
        <div className="relative flex-1 overflow-hidden">
          
          {/* Chat Container - Scrolls independently */}
          <div className="absolute inset-0 z-0">
            <ChatPanel messages={messages} mode={mode} onExample={send} loading={loading} elapsed={elapsed} displayName={displayName} />
          </div>

          {/* 
            Floating Search Bar - Locked to the bottom.
            pointer-events-none lets you click "through" the gradient to interact with the chat below.
          */}
          <div className="pointer-events-none absolute bottom-0 left-0 z-20 w-full bg-linear-to-t from-[#0d1117] via-[#0d1117]/90 to-transparent pb-6 pt-16">
            <div className="pointer-events-auto">
              <CommandInput value={input} onChange={setInput} onSubmit={() => send(input)} mode={mode} disabled={loading} />
            </div>
          </div>

        </div>
      </main>
    </div>
  )
}