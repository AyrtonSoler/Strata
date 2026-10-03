import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import { Spinner } from './ui'

interface Source {
  rule_id: string
  doc_id: string | null
  url: string
  retrieved_at: string | null
  citation: string
  title: string
  quoted_span: string
  source_origin: string | null
  available: boolean
  text: string | null
  highlight: [number, number] | null
}

export default function EvidenceSheet({ ruleId, s, onClose }: { ruleId: string; s: Strings; onClose: () => void }) {
  const [src, setSrc] = useState<Source | null>(null)
  const markRef = useRef<HTMLElement>(null)

  useEffect(() => {
    api<Source>(`/source/${ruleId}`).then(setSrc)
  }, [ruleId])

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [src])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="backdrop-in fixed inset-0 z-[1000] flex items-end justify-center bg-black/30 backdrop-blur-sm sm:items-center sm:p-6" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="sheet-up flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-[28px] bg-white shadow-2xl sm:rounded-[28px]"
      >
        <header className="flex items-start justify-between gap-4 border-b border-hairline/70 px-7 pb-5 pt-6">
          <div className="min-w-0">
            <p className="eyebrow">{src?.doc_id ?? '…'} · Evidence</p>
            <h2 className="mt-1 text-[22px] font-semibold tracking-tight">{src?.citation ?? '…'}</h2>
            {src && (
              <p className="mt-1 truncate text-[13px] text-muted">
                {src.title} · {s.retrieved} {src.retrieved_at}
              </p>
            )}
          </div>
          <button onClick={onClose} aria-label="Close" className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-fill text-muted hover:text-ink">
            ✕
          </button>
        </header>

        <div className="overflow-y-auto px-7 py-6">
          {!src && <Spinner label={s.loading} />}
          {src && src.available && src.text && (
            <article className="whitespace-pre-wrap text-[15px] leading-7 text-ink-2">
              {src.highlight ? (
                <>
                  {src.text.slice(0, src.highlight[0])}
                  <mark ref={markRef} className="evidence">
                    {src.text.slice(src.highlight[0], src.highlight[1])}
                  </mark>
                  {src.text.slice(src.highlight[1])}
                </>
              ) : (
                src.text
              )}
            </article>
          )}
          {src && !src.available && (
            <div className="space-y-5">
              <p className="text-[14px] text-muted">{s.sourceUnavailable}</p>
              <blockquote className="rounded-2xl bg-[#fffbe6] p-5 text-[16px] leading-7 text-ink">“{src.quoted_span}”</blockquote>
            </div>
          )}
        </div>

        {src && (
          <footer className="flex items-center justify-between gap-4 border-t border-hairline/70 px-7 py-4">
            <span className="truncate text-[12px] text-faint">{src.url}</span>
            <a href={src.url} target="_blank" rel="noreferrer" className="btn-ghost shrink-0">
              Original ↗
            </a>
          </footer>
        )}
      </div>
    </div>
  )
}
