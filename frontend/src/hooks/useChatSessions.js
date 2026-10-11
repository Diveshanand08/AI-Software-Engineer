/**
 * frontend/src/hooks/useChatSessions.js
 * Custom hook managing chat history, active session switching, and message persistence.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { api } from '../services/api'

export function useChatSessions(userEmail) {
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [historyList, setHistoryList] = useState([])
  const skipSessionLoadRef = useRef(false)

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.getSessions(userEmail)
      setHistoryList(data)
    } catch (e) {
      console.error('Failed to fetch history:', e)
    }
  }, [userEmail])

  useEffect(() => {
    setActiveSessionId(null)
    setMessages([])
    fetchHistory()
  }, [userEmail, fetchHistory])

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
        const data = await api.getSessionMessages(activeSessionId)
        const formatted = data.map((m) => ({ ...m, id: crypto.randomUUID() }))
        setMessages(formatted)
      } catch (e) {
        console.error('Failed to load session:', e)
      }
    }
    loadPastChat()
  }, [activeSessionId])

  const appendMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, msg])
  }, [])

  const updateMessage = useCallback((id, updater) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? updater(msg) : msg))
    )
  }, [])

  const startNewChat = useCallback(() => {
    setActiveSessionId(null)
    setMessages([])
  }, [])

  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        await api.deleteSession(id)
        if (activeSessionId === id) {
          setActiveSessionId(null)
          setMessages([])
        }
        fetchHistory()
      } catch (e) {
        console.error('Failed to delete session:', e)
      }
    },
    [activeSessionId, fetchHistory]
  )

  return {
    activeSessionId,
    setActiveSessionId,
    messages,
    setMessages,
    historyList,
    fetchHistory,
    appendMessage,
    updateMessage,
    startNewChat,
    handleDeleteSession,
    skipSessionLoadRef,
  }
}
