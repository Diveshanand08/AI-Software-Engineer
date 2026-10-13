/**
 * frontend/src/services/api.js
 * Centralized API client isolating network transport and error handling from UI components.
 */

import { API_BASE } from '../config/env'

export const api = {
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`)
      return { ok: res.ok }
    } catch {
      return { ok: false }
    }
  },

  async getProviders() {
    const res = await fetch(`${API_BASE}/providers`)
    if (!res.ok) throw new Error('Failed to fetch providers')
    return res.json()
  },

  async getCollections() {
    const res = await fetch(`${API_BASE}/collections`)
    if (!res.ok) throw new Error('Failed to fetch collections')
    return res.json()
  },

  async getSessions(userEmail = '') {
    const query = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : ''
    const res = await fetch(`${API_BASE}/sessions${query}`)
    if (!res.ok) throw new Error('Failed to fetch sessions')
    return res.json()
  },

  async getSessionMessages(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`)
    if (!res.ok) throw new Error('Failed to fetch session messages')
    return res.json()
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' })
    if (!res.ok && res.status !== 204) throw new Error('Failed to delete session')
  },

  async startIndex(name, repoUrl = null, localPath = null) {
    const res = await fetch(`${API_BASE}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, repo_url: repoUrl, local_path: localPath }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `Indexing request failed: ${res.status}`)
    }
    return res.json()
  },

  async getIndexStatus(name) {
    const res = await fetch(`${API_BASE}/index/status/${encodeURIComponent(name)}`)
    if (!res.ok) throw new Error('Failed to fetch indexing status')
    return res.json()
  },

  async findBugs(filePath, collection = '', provider = 'ollama') {
    const res = await fetch(`${API_BASE}/bugs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, collection, provider }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `Bug detection failed: ${res.status}`)
    }
    return res.json()
  },

  async runAgent(task, sessionId = null, userEmail = '') {
    const res = await fetch(`${API_BASE}/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task,
        session_id: sessionId,
        user_email: userEmail,
        model: 'phi3',
      }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `Agent execution failed: ${res.status}`)
    }
    return res.json()
  },

  async generateTests(collection, target, sessionId = null, userEmail = '') {
    const res = await fetch(`${API_BASE}/tests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        collection,
        target,
        session_id: sessionId,
        user_email: userEmail,
        model: 'phi3',
      }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `Test generation failed: ${res.status}`)
    }
    return res.json()
  },

  async createPullRequest(repoFullName, filePath, codeContent, title, description = '') {
    const res = await fetch(`${API_BASE}/pr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo_full_name: repoFullName,
        file_path: filePath,
        code_content: codeContent,
        title,
        description,
      }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(err || `Failed to create PR: ${res.status}`)
    }
    return res.json()
  },

  async streamPrompt(endpoint, body, onChunk, onSessionId) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errText = await res.text()
      throw new Error(errText || `Server error: ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const sessionMatch = buffer.match(/__SESSION_ID__:(.+?)\n\n/)
      if (sessionMatch) {
        onSessionId(sessionMatch[1])
        buffer = buffer.replace(sessionMatch[0], '')
      }

      if (buffer.includes('__SESSION_ID') && !sessionMatch) {
        continue
      }

      if (buffer.length > 0) {
        onChunk(buffer)
        buffer = ''
      }
    }
  },
}
