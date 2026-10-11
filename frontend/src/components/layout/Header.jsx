/**
 * frontend/src/components/layout/Header.jsx
 * Top navigation header displaying mode title, collection selector, model picker, and auth.
 */

import { Menu, Plus, GitBranch, Settings2, LogOut } from 'lucide-react'
import { GoogleLogin } from '@react-oauth/google'
import { ModelPicker } from '../codeassist/ModelPicker'
import { MODE_TITLES, API_BASE } from '../../config/env'

export function Header({
  mode,
  collection,
  availableCollections,
  onCollectionChange,
  onOpenSidebar,
  onNewChat,
  onOpenPRModal,
  provider,
  onProviderChange,
  user,
  displayName,
  onLogin,
  onLogout,
}) {
  return (
    <header className="glass shrink-0 flex items-center justify-between border-b px-4 py-3 md:px-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="mr-2 flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          title="Toggle Navigation Menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h1 className="font-mono text-sm font-semibold tracking-tight text-foreground">
          {MODE_TITLES[mode] || 'Chat'}
        </h1>

        <div className="hidden sm:flex items-center gap-1 rounded-lg border border-border bg-secondary/50 px-2 py-1 font-mono text-xs text-muted-foreground">
          <span className="text-blue-400">#</span>
          <select
            value={collection}
            onChange={(e) => onCollectionChange(e.target.value)}
            className="bg-transparent text-gray-200 outline-none cursor-pointer text-xs font-mono pr-1"
            title="Select indexed repository collection"
          >
            {Array.from(new Set([collection, ...availableCollections])).map((c) => (
              <option key={c} value={c} className="bg-[#1e1f20] text-gray-200">
                {c}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1 font-mono text-xs text-muted-foreground transition-colors hover:bg-secondary/70 hover:text-foreground active:scale-95"
          title="Start a new chat"
        >
          <Plus className="h-3.5 w-3.5 text-blue-400" />
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <ModelPicker apiBase={API_BASE} value={provider} onChange={onProviderChange} />

        <button
          type="button"
          onClick={onOpenPRModal}
          aria-label="Create Pull Request"
          title="Create Pull Request on GitHub"
          className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1 text-xs font-mono text-muted-foreground transition-colors hover:bg-secondary/70 hover:text-foreground active:scale-95"
        >
          <GitBranch className="h-3.5 w-3.5 text-emerald-400" />
          <span className="hidden sm:inline">Open PR</span>
        </button>

        <button
          type="button"
          aria-label="Settings"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-secondary/40 text-muted-foreground transition-colors hover:text-foreground"
        >
          <Settings2 className="h-4 w-4" />
        </button>

        {user ? (
          <div className="flex items-center gap-2 ml-1">
            {user.picture ? (
              <img
                src={user.picture}
                alt={displayName}
                className="h-7 w-7 rounded-full ring-1 ring-white/20"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 font-mono text-xs font-bold text-white">
                {displayName ? displayName[0].toUpperCase() : 'U'}
              </div>
            )}
            <button
              onClick={onLogout}
              title="Sign out"
              className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-white/10 hover:text-white transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="ml-1 scale-75 origin-right">
            <GoogleLogin
              onSuccess={onLogin}
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
  )
}
