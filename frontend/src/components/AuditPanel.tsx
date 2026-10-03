import type { Strings } from '../lib/i18n'
import type { AuditBlock, Check } from '../lib/types'

const ICON: Record<Check['outcome'], { mark: string; cls: string }> = {
  met: { mark: '✓', cls: 'bg-applies-bg text-applies' },
  not_met: { mark: '✕', cls: 'bg-[#fff2f2] text-[#c4182b]' },
  unknown: { mark: '?', cls: 'bg-unknown-bg text-unknown' },
}

export function ChecksList({ checks }: { checks: Check[] }) {
  return (
    <ul className="space-y-1.5">
      {checks.map((c, i) => (
        <li key={i} className="flex items-start gap-2.5 text-[13px] leading-snug">
          <span className={`mt-px grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full text-[11px] font-bold ${ICON[c.outcome].cls}`}>
            {ICON[c.outcome].mark}
          </span>
          <span className="text-ink-2">
            <span className="font-semibold">{c.test}.</span> {c.detail}
          </span>
        </li>
      ))}
    </ul>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="eyebrow mb-2">{title}</p>
      {children}
    </div>
  )
}

function Steps({ items }: { items: string[] }) {
  return (
    <ol className="space-y-1.5">
      {items.map((x, i) => (
        <li key={i} className="flex gap-2 text-[13px] leading-snug text-ink-2">
          <span className="tabular-nums text-faint">{i + 1}.</span>
          <span>{x}</span>
        </li>
      ))}
    </ol>
  )
}

export default function AuditPanel({ audit, penalty, s, onSource }: { audit: AuditBlock; penalty?: string | null; s: Strings; onSource: () => void }) {
  const a = s.audit
  const f = audit.facts_used
  return (
    <div className="mt-4 space-y-5 rounded-2xl bg-fill/70 p-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Section title={a.source}>
          <p className="text-[13px] text-ink-2">
            <span
              className={`mr-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                audit.source.official_corpus ? 'bg-applies-bg text-applies' : 'bg-unknown-bg text-unknown'
              }`}
            >
              {audit.source.official_corpus ? a.official : a.secondary}
            </span>
            {audit.source.doc_id} · {s.retrieved} {audit.source.retrieved_at}
          </p>
          <button onClick={onSource} className="btn-ghost -ml-3 mt-1">
            {s.source} →
          </button>
        </Section>
        <Section title={`${a.status} · ${audit.as_of}`}>
          <p className="text-[13px] leading-snug text-ink-2">{audit.status_reason}</p>
          {penalty && (
            <p className="mt-2 text-[13px] leading-snug text-ink-2">
              <span className="font-semibold">{a.penalty}.</span> {penalty}
            </p>
          )}
        </Section>
      </div>

      <Section title={a.facts}>
        <p className="text-[13px] text-ink-2">
          {f.year_built ? `Built ${f.year_built}` : s.yearUnknown} · {f.units != null ? `${f.units} units` : f.units_min ? `${f.units_min}+ units` : s.unitsUnknown}
          <span className="text-faint"> · {f.units_basis}</span>
        </p>
      </Section>

      <Section title={a.checks}>
        <ChecksList checks={audit.checks} />
      </Section>

      <div className="grid gap-5 sm:grid-cols-2">
        <Section title={a.ai}>
          <Steps items={audit.ai_steps} />
        </Section>
        <Section title={a.code}>
          <Steps items={audit.code_steps} />
        </Section>
      </div>

      <Section title={a.boundary}>
        <ul className="space-y-1">
          {audit.boundary.map((b, i) => (
            <li key={i} className="flex gap-2 text-[13px] leading-snug text-muted">
              <span>—</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={`${a.confidence} · ${audit.confidence ?? '—'}`}>
        <div className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-hairline">
          <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round((audit.confidence ?? 0) * 100)}%` }} />
        </div>
        <ul className="mt-2 space-y-0.5">
          {audit.confidence_signals.map((x, i) => (
            <li key={i} className="text-[12px] text-muted">
              {x}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
