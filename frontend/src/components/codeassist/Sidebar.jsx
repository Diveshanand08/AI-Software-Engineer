import { MessagesSquare, FileCode2, Bug, Database, Github, FolderGit2, Loader2, Bot, Plus, Clock, X, Trash2 } from 'lucide-react'
import { cn } from '../../lib/utils'

const NAV_ITEMS = [
  { id: 'chat', label: 'Chat', icon: MessagesSquare, desc: 'Ask about your codebase' },
  { id: 'explain', label: 'Explain', icon: FileCode2, desc: 'Break down any function' },
  { id: 'bugs', label: 'Find Bugs', icon: Bug, desc: 'Detect issues & smells' },
  { id: 'agent', label: 'Auto-Coder', icon: Bot, desc: 'AI writes & tests code' },
]

export function Sidebar({ 
  isOpen,
  onClose,
  mode, 
  onModeChange, 
  collection, 
  onCollectionChange, 
  status, 
  repoUrl, 
  onRepoUrlChange, 
  onImport, 
  isIndexing,
  historyList = [],
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession
}) {
  return (
    <>
      {/* Dimmed Background Overlay */}
      <div 
        className={cn(
          "fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      {/* Floating Drawer */}
      <aside 
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-full w-72 flex-col border-r border-white/10 bg-[#0d1117] shadow-2xl transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-white/10 px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 shadow-[0_0_15px_-5px] shadow-blue-500/50">
              <Database className="h-4 w-4 text-white" />
            </div>
            <span className="font-mono text-sm font-semibold tracking-tight text-white">
              CodeAssist
            </span>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-1 flex-col overflow-y-auto p-4 gap-8">
          
          {/* IMPORT REPO SECTION */}
          <div>
            <h3 className="mb-3 flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-gray-500">
              <FolderGit2 className="h-3.5 w-3.5" />
              Import Repository
            </h3>
            <div className="flex flex-col gap-2">
              <div className="relative">
                <Github className="absolute left-2.5 top-2 h-4 w-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="https://github.com/.../repo.git"
                  value={repoUrl}
                  onChange={(e) => onRepoUrlChange(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-[#21262d]/50 py-1.5 pl-9 pr-3 font-mono text-xs text-gray-200 placeholder:text-gray-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />
              </div>
              <input
                type="text"
                placeholder="Collection Name (e.g. test_repo)"
                value={collection}
                onChange={(e) => onCollectionChange(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-[#21262d]/50 px-3 py-1.5 font-mono text-xs text-gray-200 placeholder:text-gray-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
              <button
                onClick={onImport}
                disabled={isIndexing || !repoUrl || !collection}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600/10 py-1.5 font-mono text-xs font-semibold text-blue-500 transition-colors hover:bg-blue-600/20 disabled:opacity-50"
              >
                {isIndexing ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Indexing...
                  </>
                ) : (
                  'Clone & Index'
                )}
              </button>
            </div>
          </div>

          {/* MODE SECTION */}
          <div>
            <h3 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-wider text-gray-500">
              Mode
            </h3>
            <nav className="flex flex-col gap-1.5">
              {NAV_ITEMS.map((item) => {
                const isActive = mode === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onModeChange(item.id)
                      onClose() // Auto-close on mobile/selection if desired
                    }}
                    className={cn(
                      'group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all',
                      isActive 
                        ? 'border border-blue-500/20 bg-blue-500/10 shadow-[0_0_15px_-5px] shadow-blue-500/20' 
                        : 'border border-transparent hover:bg-white/5'
                    )}
                  >
                    <div className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors',
                      isActive 
                        ? 'border-blue-500/30 bg-blue-500 text-white shadow-[0_0_10px_-2px] shadow-blue-500/50' 
                        : 'border-white/10 bg-[#21262d] text-gray-400 group-hover:text-gray-200'
                    )}>
                      <item.icon className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col items-start text-left">
                      <span className={cn(
                        'font-mono text-sm font-medium transition-colors',
                        isActive ? 'text-white' : 'text-gray-300 group-hover:text-white'
                      )}>
                        {item.label}
                      </span>
                      <span className="font-mono text-[10px] text-gray-500">
                        {item.desc}
                      </span>
                    </div>
                    {isActive && (
                      <div className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
                    )}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* CHAT HISTORY SECTION */}
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                <Clock className="h-3.5 w-3.5" />
                History
              </h3>
              <button
                onClick={onNewChat}
                className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-500/10 text-blue-500 transition-colors hover:bg-blue-500/20"
                title="Start New Chat"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-1 space-y-1">
              {historyList.length === 0 ? (
                <div className="py-4 text-center font-mono text-[11px] text-gray-600">
                  No previous chats
                </div>
              ) : (
                historyList.map(session => (
                  <div
                    key={session.id}
                    className={cn(
                      'group flex items-center gap-1 rounded-md transition-colors',
                      activeSessionId === session.id
                        ? 'bg-blue-500/10'
                        : 'hover:bg-white/5'
                    )}
                  >
                    <button
                      onClick={() => onSelectSession(session.id)}
                      className={cn(
                        'flex-1 truncate px-3 py-2 text-left font-mono text-[11px] transition-colors',
                        activeSessionId === session.id
                          ? 'font-medium text-blue-400'
                          : 'text-gray-400 group-hover:text-gray-200'
                      )}
                    >
                      {session.title || 'New Conversation'}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id) }}
                      title="Delete conversation"
                      className="mr-1 shrink-0 rounded p-1 text-gray-600 opacity-0 transition-all group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-400"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

        <div className="p-4 shrink-0 border-t border-white/5 bg-[#0d1117]">
          <div className="rounded-xl border border-white/10 bg-[#161b22]/50 p-3 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <div className={cn('h-2 w-2 rounded-full', status.ok ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]')} />
              <span className="font-mono text-[11px] text-gray-400">
                {status.ok ? 'backend connected' : 'backend offline'}
              </span>
            </div>
            <div className="mt-1.5 pl-4 font-mono text-[10px] text-gray-600">
              localhost:8000
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}