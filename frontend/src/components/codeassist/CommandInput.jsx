import { useRef, useState, useEffect } from 'react'
import { ArrowUp, Mic } from 'lucide-react'

export function CommandInput({ value, onChange, onSubmit, disabled, mode }) {
  const [composing, setComposing] = useState(false)
  const inputRef = useRef(null)

  // Auto-resize the textarea to fit content
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`
    }
  }, [value])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !composing && e.nativeEvent.isComposing !== true && e.keyCode !== 229) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    if (!value.trim() || disabled) return
    onSubmit()
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
  }

  return (
    <div className="w-full px-4 md:px-8 mx-auto max-w-3xl">
      <div 
        className="relative flex flex-col w-full rounded-4xl p-3 shadow-2xl border border-white/5 transition-all focus-within:border-white/10"
        style={{ backgroundColor: '#1e1f22' }} 
      >
        {/* TOP ROW: Text Area */}
        <textarea
          ref={inputRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
          placeholder="Ask anything about your codebase..."
          spellCheck={false}
          disabled={disabled}
          className="w-full max-h-50 min-h-6 bg-transparent resize-none outline-none text-gray-100 placeholder:text-gray-400 px-3 pt-2 pb-4 text-[15px] leading-relaxed custom-scrollbar disabled:opacity-50"
        />
        
        {/* BOTTOM ROW: Toolbar Options */}
        {/* Changed to justify-end to align the remaining buttons to the right */}
        <div className="flex items-center justify-end px-2 pb-1">
          
          {/* Right Icons (Mic, Send) */}
          <div className="flex items-center gap-4 text-gray-400">
            <button type="button" className="hover:text-gray-200 transition-colors">
              <Mic className="w-5 h-5" />
            </button>
            <button
              onClick={submit}
              disabled={!value.trim() || disabled}
              className="flex h-9 w-9 items-center justify-center rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-110"
              style={{ backgroundColor: '#2563eb', color: 'white' }}
            >
              <ArrowUp className="h-5 w-5" strokeWidth={2.5} />
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}