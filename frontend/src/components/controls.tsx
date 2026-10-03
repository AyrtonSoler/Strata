import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

/** Closes a popover on outside click or Escape. */
function useDismiss(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onClose()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])
  return ref
}

const Chevron = ({ open }: { open: boolean }) => (
  <svg width="10" height="10" viewBox="0 0 12 12" className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}>
    <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export function Select<T extends string>({
  value,
  options,
  onChange,
  className = '',
  align = 'left',
}: {
  value: T
  options: [T, string][]
  onChange: (v: T) => void
  className?: string
  align?: 'left' | 'right'
}) {
  const [open, setOpen] = useState(false)
  const ref = useDismiss(open, () => setOpen(false))
  const label = options.find(([v]) => v === value)?.[1] ?? value
  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 rounded-xl bg-white/90 px-3 py-2 text-left text-[13px] font-medium text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)] ring-1 ring-hairline transition hover:ring-ink/25"
      >
        <span className="truncate">{label}</span>
        <Chevron open={open} />
      </button>
      {open && (
        <ul
          className={`sheet-up absolute z-[1200] mt-1.5 max-h-72 min-w-full overflow-auto rounded-2xl bg-white/95 p-1.5 shadow-[0_16px_40px_rgba(0,0,0,0.16)] ring-1 ring-black/5 backdrop-blur-xl ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          {options.map(([v, l]) => (
            <li key={v}>
              <button
                type="button"
                onClick={() => {
                  onChange(v)
                  setOpen(false)
                }}
                className={`flex w-full items-center justify-between gap-6 whitespace-nowrap rounded-xl px-3 py-2 text-left text-[13px] transition ${
                  v === value ? 'bg-accent text-white' : 'text-ink hover:bg-fill'
                }`}
              >
                {l}
                {v === value && <span className="text-[11px]">✓</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const pad = (n: number) => String(n).padStart(2, '0')
const iso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`

export function formatDate(value: string, lang: 'en' | 'es' = 'en', long = false) {
  const [y, m, d] = value.split('-').map(Number)
  if (!y) return value
  if (lang === 'es') return `${d} ${long ? MONTHS_ES[m - 1] : MONTHS_ES[m - 1].slice(0, 3)} ${y}`
  return `${long ? MONTHS_EN[m - 1] : MONTHS_EN[m - 1].slice(0, 3)} ${d}, ${y}`
}

export function DatePicker({
  value,
  onChange,
  min = '2000-01-01',
  max = '2035-12-31',
  presets = [],
  lang = 'en',
  trigger,
  align = 'right',
}: {
  value: string
  onChange: (v: string) => void
  min?: string
  max?: string
  presets?: [string, string][]
  lang?: 'en' | 'es'
  trigger?: (open: boolean) => ReactNode
  align?: 'left' | 'right'
}) {
  const [open, setOpen] = useState(false)
  const ref = useDismiss(open, () => setOpen(false))
  const [vy, vm] = value.split('-').map(Number)
  const [view, setView] = useState({ y: vy || 2026, m: (vm || 1) - 1 })
  useEffect(() => {
    if (open) setView({ y: vy, m: vm - 1 })
  }, [open, vy, vm])

  const cells = useMemo(() => {
    const first = new Date(Date.UTC(view.y, view.m, 1)).getUTCDay()
    const days = new Date(Date.UTC(view.y, view.m + 1, 0)).getUTCDate()
    return [...Array(first).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)]
  }, [view])
  const months = lang === 'es' ? MONTHS_ES : MONTHS_EN
  const week = lang === 'es' ? ['D', 'L', 'M', 'M', 'J', 'V', 'S'] : ['S', 'M', 'T', 'W', 'T', 'F', 'S']
  const shift = (k: number) => {
    const m = view.m + k
    setView({ y: view.y + Math.floor(m / 12), m: ((m % 12) + 12) % 12 })
  }
  const minY = Number(min.slice(0, 4))
  const maxY = Number(max.slice(0, 4))

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)} className="block text-left">
        {trigger ? (
          trigger(open)
        ) : (
          <span className="flex items-center gap-2 rounded-full bg-white/90 px-3 py-1.5 text-[13px] font-medium text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)] ring-1 ring-hairline transition hover:ring-ink/25">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <rect x="3" y="5" width="18" height="16" rx="3" />
              <path d="M3 10h18M8 3v4M16 3v4" />
            </svg>
            {formatDate(value, lang)}
            <Chevron open={open} />
          </span>
        )}
      </button>
      {open && (
        <div
          className={`sheet-up absolute z-[1200] mt-2 w-[296px] rounded-[22px] bg-white/95 p-4 shadow-[0_20px_50px_rgba(0,0,0,0.18)] ring-1 ring-black/5 backdrop-blur-xl ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex">
              <button type="button" onClick={() => shift(-12)} disabled={view.y <= minY} className="grid h-8 w-7 place-items-center rounded-full text-ink-2 hover:bg-fill disabled:opacity-30" aria-label="Previous year">
                «
              </button>
              <button type="button" onClick={() => shift(-1)} className="grid h-8 w-7 place-items-center rounded-full text-ink-2 hover:bg-fill" aria-label="Previous month">
                ‹
              </button>
            </div>
            <p className="text-[15px] font-semibold capitalize tabular-nums">
              {months[view.m]} {view.y}
            </p>
            <div className="flex">
              <button type="button" onClick={() => shift(1)} className="grid h-8 w-7 place-items-center rounded-full text-ink-2 hover:bg-fill" aria-label="Next month">
                ›
              </button>
              <button type="button" onClick={() => shift(12)} disabled={view.y >= maxY} className="grid h-8 w-7 place-items-center rounded-full text-ink-2 hover:bg-fill disabled:opacity-30" aria-label="Next year">
                »
              </button>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-7 gap-1 text-center text-[11px] font-semibold text-faint">
            {week.map((w, i) => (
              <span key={i}>{w}</span>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (d === null) return <span key={`b${i}`} />
              const v = iso(view.y, view.m, d)
              const disabled = v < min || v > max
              const selected = v === value
              return (
                <button
                  key={v}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    onChange(v)
                    setOpen(false)
                  }}
                  className={`grid h-9 place-items-center rounded-full text-[13px] tabular-nums transition ${
                    selected ? 'bg-accent font-semibold text-white' : disabled ? 'text-hairline' : 'text-ink hover:bg-fill'
                  }`}
                >
                  {d}
                </button>
              )
            })}
          </div>
          {presets.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5 border-t border-hairline/60 pt-3">
              {presets.map(([v, label]) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => {
                    onChange(v)
                    setOpen(false)
                  }}
                  className={`rounded-full px-2.5 py-1 text-[12px] font-medium transition ${v === value ? 'bg-accent text-white' : 'bg-fill text-ink-2 hover:bg-hairline/60'}`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
