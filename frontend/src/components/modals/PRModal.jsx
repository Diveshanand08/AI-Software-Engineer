/**
 * frontend/src/components/modals/PRModal.jsx
 * Modal dialog for generating and opening Pull Requests on GitHub.
 */

import { useState } from 'react'
import { GitBranch, X, ExternalLink, Loader2 } from 'lucide-react'
import { api } from '../../services/api'

export function PRModal({ isOpen, onClose }) {
  const [prRepo, setPrRepo] = useState('Diveshanand08/AI-Software-Engineer')
  const [prFile, setPrFile] = useState('')
  const [prTitle, setPrTitle] = useState('fix: patch detected issue')
  const [prContent, setPrContent] = useState('')
  const [isCreatingPr, setIsCreatingPr] = useState(false)
  const [prResult, setPrResult] = useState(null)
  const [prError, setPrError] = useState(null)

  if (!isOpen) return null

  const handleClose = () => {
    onClose()
    setPrResult(null)
    setPrError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prRepo || !prFile || !prContent || !prTitle) return

    setIsCreatingPr(true)
    setPrError(null)
    setPrResult(null)

    try {
      const data = await api.createPullRequest(
        prRepo.trim(),
        prFile.trim(),
        prContent,
        prTitle.trim()
      )
      setPrResult(data)
    } catch (err) {
      setPrError(err.message)
    } finally {
      setIsCreatingPr(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#161b22] p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <GitBranch className="h-4 w-4" />
            </span>
            <h2 className="text-base font-semibold text-white">Create GitHub Pull Request</h2>
          </div>
          <button
            onClick={handleClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-white/10 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {prResult ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-300 space-y-3">
            <p className="font-semibold text-sm">🎉 {prResult.message}</p>
            <a
              href={prResult.pr_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-black hover:bg-emerald-400 transition-colors"
            >
              View Pull Request on GitHub <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3 text-xs">
            {prError && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-2.5 text-rose-300">
                {prError}
              </div>
            )}
            <div>
              <label className="block mb-1 text-gray-400 font-medium">GitHub Repository</label>
              <input
                type="text"
                value={prRepo}
                onChange={(e) => setPrRepo(e.target.value)}
                required
                placeholder="owner/repo"
                className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-mono text-gray-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block mb-1 text-gray-400 font-medium">File Path in Repo</label>
              <input
                type="text"
                value={prFile}
                onChange={(e) => setPrFile(e.target.value)}
                required
                placeholder="e.g. test_fix_content.py"
                className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-mono text-gray-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block mb-1 text-gray-400 font-medium">PR Title</label>
              <input
                type="text"
                value={prTitle}
                onChange={(e) => setPrTitle(e.target.value)}
                required
                className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 text-gray-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block mb-1 text-gray-400 font-medium">Code Content</label>
              <textarea
                rows={5}
                value={prContent}
                onChange={(e) => setPrContent(e.target.value)}
                required
                className="w-full rounded-lg border border-white/10 bg-[#0d1117] px-3 py-2 font-mono text-gray-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg border border-white/10 px-3 py-2 text-gray-400 hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreatingPr}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {isCreatingPr ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {isCreatingPr ? 'Pushing & Opening PR...' : 'Create PR'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
