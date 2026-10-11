/**
 * frontend/src/App.jsx
 * Clean, modular application entrypoint.
 * Business logic, network transport, and state machines are delegated to custom hooks and services.
 */

import { useState, useEffect, useCallback } from 'react'
import { Sidebar } from './components/codeassist/Sidebar.jsx'
import { ChatPanel } from './components/codeassist/ChatPanel.jsx'
import { CommandInput } from './components/codeassist/CommandInput.jsx'
import { Header } from './components/layout/Header.jsx'
import { PRModal } from './components/modals/PRModal.jsx'
import { useAuth } from './lib/useAuth.js'
import { useIndexing } from './hooks/useIndexing.js'
import { useChatSessions } from './hooks/useChatSessions.js'
import { api } from './services/api.js'
import { API_BASE } from './config/env.js'

export default function App() {
  const { user, displayName, login, logout } = useAuth()
  const [mode, setMode] = useState('chat')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isPrModalOpen, setIsPrModalOpen] = useState(false)
  const [provider, setProvider] = useState(() => localStorage.getItem('provider') || 'ollama')

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [status, setStatus] = useState({ ok: false })

  // Custom Domain Hooks
  const {
    collection,
    setCollection,
    repoUrl,
    setRepoUrl,
    isIndexing,
    indexStatusMsg,
    availableCollections,
    handleImport,
    cancelIndexing,
  } = useIndexing()

  const {
    activeSessionId,
    setActiveSessionId,
    messages,
    historyList,
    fetchHistory,
    appendMessage,
    updateMessage,
    startNewChat,
    handleDeleteSession,
    skipSessionLoadRef,
  } = useChatSessions(user?.email)

  // Track backend connectivity
  useEffect(() => {
    api.checkHealth().then(setStatus)
  }, [])

  // Timer for active AI generation
  useEffect(() => {
    let timer
    if (loading) {
      setElapsed(0)
      timer = setInterval(() => setElapsed((e) => e + 1), 1000)
    }
    return () => clearInterval(timer)
  }, [loading])

  const handleProviderChange = (p) => {
    setProvider(p)
    localStorage.setItem('provider', p)
  }

  // Unified message dispatcher for chat, explain, bug analysis, auto-coder, and tests
  const handleSend = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    appendMessage({ id: crypto.randomUUID(), role: 'user', content: trimmed })
    setInput('')
    setLoading(true)

    try {
      if (mode === 'bugs') {
        const data = await api.findBugs(trimmed)
        appendMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.analysis || 'No bugs detected or no response.',
        })
      } else if (mode === 'agent') {
        const data = await api.runAgent(trimmed, activeSessionId, user?.email || '')
        if (data.session_id) {
          setActiveSessionId(data.session_id)
          fetchHistory()
        }
        const statusBadge = data.success
          ? `✅ **Auto-Coder Solved Task!** (in ${data.attempts} attempt${data.attempts > 1 ? 's' : ''})`
          : `❌ **Auto-Coder Failed** (${data.attempts} attempts reached)`
        const content = `${statusBadge}\n\n\`\`\`python\n${data.code}\n\`\`\`\n\n**Docker Sandbox Execution Output:**\n\`\`\`\n${
          data.stdout || data.stderr || data.error || 'No output.'
        }\n\`\`\``
        appendMessage({ id: crypto.randomUUID(), role: 'assistant', content })
      } else if (mode === 'tests') {
        const data = await api.generateTests(collection, trimmed, activeSessionId, user?.email || '')
        if (data.session_id) {
          setActiveSessionId(data.session_id)
          fetchHistory()
        }
        const statusBadge = data.success
          ? `✅ **Unit Tests Passed in Docker!** (${data.attempts} attempt${data.attempts > 1 ? 's' : ''})`
          : `⚠️ **Tests Failed in Docker Sandbox**`
        const content = `${statusBadge}\n\n\`\`\`python\n${data.code}\n\`\`\`\n\n**Test Runner Output:**\n\`\`\`\n${
          data.stdout || data.error || 'No output.'
        }\n\`\`\``
        appendMessage({ id: crypto.randomUUID(), role: 'assistant', content })
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

        const msgId = crypto.randomUUID()
        appendMessage({ id: msgId, role: 'assistant', content: '' })

        await api.streamPrompt(
          endpoint,
          body,
          (chunk) => {
            updateMessage(msgId, (msg) => ({ ...msg, content: msg.content + chunk }))
          },
          (newSessionId) => {
            skipSessionLoadRef.current = true
            setActiveSessionId(newSessionId)
            fetchHistory()
          }
        )
      }
    } catch (e) {
      appendMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${e.message}`,
      })
    } finally {
      setLoading(false)
    }
  }

  const onNewChatClick = useCallback(() => {
    startNewChat()
    setIsSidebarOpen(false)
  }, [startNewChat])

  return (
    <div className="bg-grid fixed inset-0 flex overflow-hidden bg-background">
      <div className="glow-amber pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full blur-3xl" />
      <div className="glow-amber pointer-events-none absolute -bottom-40 right-10 h-96 w-96 rounded-full opacity-60 blur-3xl" />

      {/* Navigation & Repository Sidebar */}
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
        indexStatusMsg={indexStatusMsg}
        onCancelIndex={cancelIndexing}
        apiBase={API_BASE}
        historyList={historyList}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id)
          setIsSidebarOpen(false)
        }}
        onNewChat={onNewChatClick}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main Content Workspace */}
      <main className="relative z-10 flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        <Header
          mode={mode}
          collection={collection}
          availableCollections={availableCollections}
          onCollectionChange={setCollection}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          onNewChat={onNewChatClick}
          onOpenPRModal={() => setIsPrModalOpen(true)}
          provider={provider}
          onProviderChange={handleProviderChange}
          user={user}
          displayName={displayName}
          onLogin={login}
          onLogout={logout}
        />

        <div className="relative flex-1 overflow-hidden">
          <div className="absolute inset-0 z-0">
            <ChatPanel
              messages={messages}
              mode={mode}
              onExample={handleSend}
              loading={loading}
              elapsed={elapsed}
              displayName={displayName}
              historyList={historyList}
              onSelectSession={(id) => setActiveSessionId(id)}
            />
          </div>

          <div className="pointer-events-none absolute bottom-0 left-0 z-20 w-full bg-linear-to-t from-[#0d1117] via-[#0d1117]/90 to-transparent pb-6 pt-16">
            <div className="pointer-events-auto">
              <CommandInput
                value={input}
                onChange={setInput}
                onSubmit={() => handleSend(input)}
                mode={mode}
                disabled={loading}
              />
            </div>
          </div>
        </div>
      </main>

      <PRModal isOpen={isPrModalOpen} onClose={() => setIsPrModalOpen(false)} />
    </div>
  )
}