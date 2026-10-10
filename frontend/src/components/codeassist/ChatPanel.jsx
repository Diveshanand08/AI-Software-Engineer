import { useEffect, useRef, useState } from 'react'
import { Sparkles, Check, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '../../lib/utils'

function CodeBlock({ inline, className, children, ...props }) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const codeString = String(children).replace(/\n$/, '')

  const copyToClipboard = () => {
    navigator.clipboard.writeText(codeString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!inline && match) {
    return (
      <div className="mb-6 overflow-hidden rounded-xl border border-white/10 bg-[#1e1f20] text-[14px]">
        <div className="flex items-center justify-between bg-[#282a2c] px-4 py-2">
          <span className="font-mono text-xs text-gray-400">{match[1]}</span>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? <span className="text-green-500">Copied!</span> : 'Copy code'}
          </button>
        </div>
        <SyntaxHighlighter
          {...props}
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          customStyle={{ margin: 0, background: 'transparent', padding: '1rem' }}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    )
  }
  
  return (
    <code {...props} className={cn(className, "rounded-md bg-[#282a2c] px-1.5 py-0.5 font-mono text-[13px] text-blue-200")}>
      {children}
    </code>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end w-full mb-8">
        <div className="max-w-[80%] rounded-3xl bg-[#1e1f20] px-5 py-3.5 text-[15px] leading-relaxed text-gray-100 whitespace-pre-wrap shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex w-full gap-4 mb-8">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center mt-1">
        <Sparkles className="h-6 w-6 text-[#a8c7fa]" />
      </div>
      <div className="flex-1 min-w-0 text-[15px] leading-relaxed text-gray-100">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({children}) => <p className="mb-4 last:mb-0 text-gray-200">{children}</p>,
            a: ({children, href}) => <a href={href} className="text-[#a8c7fa] hover:underline">{children}</a>,
            ul: ({children}) => <ul className="mb-4 list-disc pl-6 last:mb-0 space-y-1">{children}</ul>,
            ol: ({children}) => <ol className="mb-4 list-decimal pl-6 last:mb-0 space-y-1">{children}</ol>,
            li: ({children}) => <li>{children}</li>,
            code: CodeBlock
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

export function ChatPanel({ messages = [], onExample, loading }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex h-full flex-col px-4 pt-16 md:pt-24 max-w-200 mx-auto overflow-y-auto">
        <div className="mb-12">
          <h1 className="text-[44px] font-medium leading-tight bg-linear-to-r from-[#4285f4] via-[#d96570] to-[#f4b400] text-transparent bg-clip-text">
            Hello, Divesh
          </h1>
          <h2 className="text-[44px] font-medium leading-tight text-[#444746]">
            How can I help you today?
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            'Explain how chunk_python_file works',
            'Find bugs in indexer.py',
            'Write a script to fetch weather data',
            'What does the retriever return?'
          ].map((ex) => (
            <button
              key={ex}
              onClick={() => onExample(ex)}
              className="flex items-center rounded-2xl bg-[#1e1f20] hover:bg-[#282a2c] p-4 text-left text-[15px] text-gray-300 transition-colors shadow-sm h-16"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto custom-scrollbar">
      {/* THE FIX: pb-48 reduced to pb-8 because the search bar is no longer blocking the bottom! */}
      <div className="flex flex-col min-h-full pb-44">
        <div className="flex-1" />
        <div className="mx-auto flex w-full max-w-200 flex-col px-4 pt-8 md:px-8">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {loading && (
             <div className="flex w-full gap-4 mb-8">
               <div className="flex h-8 w-8 shrink-0 items-center justify-center mt-1">
                 <Sparkles className="h-6 w-6 text-[#a8c7fa] animate-pulse" />
               </div>
             </div>
          )}
         
        </div>
      </div>
    </div>
  )
}