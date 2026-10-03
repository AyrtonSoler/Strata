import type { ReactNode } from 'react'
import type { Result } from '../lib/types'

export type Shade = Result | 'none'

export const RESULT_COLOR: Record<Shade, string> = {
  applies: '#30a14e',
  unknown: '#ff9f0a',
  not_yet_effective: '#0a84ff',
  pending: '#bf5af2',
  superseded: '#a1a1a6',
  none: '#d2d2d7',
}

const PILL: Record<Result, string> = {
  applies: 'bg-applies-bg text-applies',
  unknown: 'bg-unknown-bg text-unknown',
  not_yet_effective: 'bg-future-bg text-future',
  pending: 'bg-pending-bg text-pending',
  superseded: 'bg-superseded-bg text-superseded',
}

export function ResultBadge({ result, label }: { result: Result; label: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold ${PILL[result]}`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: RESULT_COLOR[result] }} />
      {label}
    </span>
  )
}

export function LayerTag({ level, children }: { level: 'state' | 'city'; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-muted">
      <span className={`h-2 w-2 rounded-[3px] ${level === 'state' ? 'bg-layer-state' : 'bg-layer-city'}`} />
      {children}
    </span>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-[15px] text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-hairline border-t-accent" />
      {label}
    </div>
  )
}

export function ErrorNote({ message }: { message: string }) {
  return <p className="rounded-2xl bg-[#fff2f2] px-5 py-4 text-[14px] text-[#c4182b]">{message}</p>
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  size = 'md',
}: {
  value: T
  options: [T, string][]
  onChange: (v: T) => void
  size?: 'sm' | 'md'
}) {
  return (
    <div className="inline-flex rounded-full bg-fill p-0.5">
      {options.map(([v, label]) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`rounded-full font-medium transition ${size === 'sm' ? 'px-2.5 py-1 text-[12px]' : 'px-3.5 py-1.5 text-[13px]'} ${
            value === v ? 'bg-white text-ink shadow-[0_1px_3px_rgba(0,0,0,0.12)]' : 'text-muted hover:text-ink'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function StrataMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <rect x="2" y="3" width="20" height="5" rx="2.5" fill="#5856d6" />
      <rect x="5" y="9.5" width="17" height="5" rx="2.5" fill="#0a9e8f" />
      <rect x="8" y="16" width="14" height="5" rx="2.5" fill="#1d1d1f" />
    </svg>
  )
}
