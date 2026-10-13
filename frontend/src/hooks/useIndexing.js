/**
 * frontend/src/hooks/useIndexing.js
 * Custom hook encapsulating repository cloning, indexing polling, and collection state.
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { api } from '../services/api'

export function useIndexing() {
  const [collection, setCollection] = useState('test_repo')
  const [repoUrl, setRepoUrl] = useState('')
  const [isIndexing, setIsIndexing] = useState(false)
  const [indexStatusMsg, setIndexStatusMsg] = useState('')
  const [availableCollections, setAvailableCollections] = useState(['test_repo'])
  const pollTimerRef = useRef(null)

  const fetchCollections = useCallback(async () => {
    try {
      const data = await api.getCollections()
      if (Array.isArray(data) && data.length > 0) {
        setAvailableCollections(data)
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchCollections()
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [fetchCollections])

  const cancelIndexing = useCallback(() => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    setIsIndexing(false)
    setIndexStatusMsg('')
  }, [])

  const handleImport = useCallback(async () => {
    const trimmedUrl = repoUrl.trim()
    const targetColl = collection.trim().replace(/\s+/g, '_').replace(/\.[a-zA-Z0-9]+$/, '')
    if (!trimmedUrl || !targetColl || isIndexing) return

    if (trimmedUrl.includes('github.com')) {
      const pathOnly = trimmedUrl.split('github.com/')[1] || ''
      const parts = pathOnly.replace(/\.git$/, '').split('/').filter(Boolean)
      if (parts.length < 2) {
        alert(
          `⚠️ Incomplete GitHub URL!\n\nYou entered a user account link:\n${trimmedUrl}\n\nGit cannot clone a user profile. Please provide a full repository URL with the project name, for example:\nhttps://github.com/${parts[0] || 'username'}/repository_name`
        )
        return
      }
    }

    try {
      setIsIndexing(true)
      setIndexStatusMsg('Initiating background clone...')

      await api.startIndex(targetColl, trimmedUrl)
      setIndexStatusMsg(`Cloning repository into ${targetColl}...`)

      let stalledAttempts = 0
      let lastMsg = ''
      let unknownAttempts = 0

      pollTimerRef.current = setInterval(async () => {
        try {
          const data = await api.getIndexStatus(targetColl)
          if (data.status === 'in_progress') {
            if (data.message) {
              setIndexStatusMsg(data.message)
              if (data.message !== lastMsg) {
                lastMsg = data.message
                stalledAttempts = 0
              } else {
                stalledAttempts++
              }
            } else {
              stalledAttempts++
            }
          } else if (data.status === 'completed') {
            clearInterval(pollTimerRef.current)
            setIsIndexing(false)
            setIndexStatusMsg('')
            setRepoUrl('')
            setCollection(targetColl)
            fetchCollections()
            alert(`🎉 Successfully indexed '${targetColl}'! You can now ask questions about this codebase.`)
            return
          } else if (data.status === 'failed') {
            clearInterval(pollTimerRef.current)
            setIsIndexing(false)
            setIndexStatusMsg('')
            alert(`❌ Indexing failed for '${targetColl}': ${data.error || 'Unknown error'}`)
            return
          } else if (data.status === 'unknown') {
            unknownAttempts++
            if (unknownAttempts >= 30) {
              clearInterval(pollTimerRef.current)
              setIsIndexing(false)
              setIndexStatusMsg('')
              alert(`⚠️ Indexing process was interrupted or server restarted. Please try again.`)
              return
            }
          }
        } catch {
          // ignore transient poll network blips
        }

        // Only time out if there has been no progress update for 5 minutes
        if (stalledAttempts >= 120) {
          clearInterval(pollTimerRef.current)
          setIsIndexing(false)
          setIndexStatusMsg('')
          alert(`⚠️ Indexing appears stalled. Please check your backend terminal.`)
        }
      }, 2500)
    } catch (e) {
      alert(`Error starting import: ${e.message}`)
      setIsIndexing(false)
      setIndexStatusMsg('')
    }
  }, [repoUrl, collection, isIndexing, fetchCollections])

  return {
    collection,
    setCollection,
    repoUrl,
    setRepoUrl,
    isIndexing,
    indexStatusMsg,
    availableCollections,
    handleImport,
    cancelIndexing,
    fetchCollections,
  }
}
