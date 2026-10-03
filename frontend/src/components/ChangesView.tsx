import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import type { ChangeTest } from '../lib/types'
import { Card, ErrorNote, Spinner } from './ui'

const TYPE_LABEL: Record<string, string> = {
  as_of: 'Effective-date change',
  boundary: 'Jurisdiction boundary',
  pending: 'Pending legislation',
  negative: 'Struck measure',
}

export default function ChangesView({ s, onOpenAddress }: { s: Strings; onOpenAddress: (id: string) => void }) {
  const [tests, setTests] = useState<ChangeTest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    api<ChangeTest[]>('/changes').then(setTests).catch((e) => setError(String(e)))
  }, [])

  if (error) return <ErrorNote message={error} />
  if (!tests) return <Spinner label={s.loading} />

  return (
    <div className="space-y-8">
      <section className="mx-auto max-w-3xl pt-6 text-center">
        <h1 className="text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[52px]">What changes, for whom.</h1>
        <p className="mx-auto mt-3 max-w-xl text-[19px] leading-snug text-muted">
          Each law change, applied to every sample address. Pending bills stay pending, and struck measures never count.
        </p>
      </section>
      <div className="grid gap-5 md:grid-cols-2">
        {tests.map((c) => {
          const id = c.test.test_id
          const flagged = new Set(c.conflict_flag_address_ids)
          return (
            <Card key={id} className="flex flex-col p-7">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">
                    {id} · {TYPE_LABEL[c.test.type ?? ''] ?? c.test.type}
                  </p>
                  <h3 className="mt-1 text-[21px] font-semibold leading-snug tracking-tight">{c.test.title ?? id}</h3>
                </div>
                <div className="text-right">
                  <p className="text-[40px] font-semibold leading-none tabular-nums tracking-tight">{c.affected_address_ids.length}</p>
                  <p className="text-[12px] text-muted">{s.affected}</p>
                </div>
              </div>
              {c.test.expected_behavior && (
                <p className="mt-4 text-[14px] leading-relaxed text-ink-2">
                  <span className="font-semibold">{s.expected}.</span> {c.test.expected_behavior}
                </p>
              )}
              <p className="mt-2 text-[13px] leading-relaxed text-muted">{c.notes}</p>
              {c.conflict_flag_address_ids.length > 0 && (
                <p className="mt-3 inline-flex w-fit rounded-full bg-unknown-bg px-3 py-1 text-[12px] font-semibold text-unknown">
                  {c.conflict_flag_address_ids.length} {s.flagged} · {s.conflict}
                </p>
              )}
              <div className="mt-auto pt-4">
                <p className="text-[12px] text-faint">
                  {s.mapped}:{' '}
                  {Object.entries(c.mapped_rules)
                    .map(([k, v]) => `${k} → ${v.join(', ') || '—'}`)
                    .join(' · ')}
                </p>
                {c.affected_address_ids.length > 0 && (
                  <button onClick={() => setOpen(open === id ? null : id)} className="btn-ghost -ml-3 mt-1">
                    {open === id ? 'Hide addresses' : 'Show addresses'}
                  </button>
                )}
                {open === id && (
                  <div className="mt-2 flex max-h-48 flex-wrap gap-1.5 overflow-auto">
                    {c.affected_address_ids.map((aid) => (
                      <button
                        key={aid}
                        onClick={() => onOpenAddress(aid)}
                        className={`rounded-md px-2 py-0.5 font-mono text-[11px] transition hover:ring-2 hover:ring-accent/40 ${
                          flagged.has(aid) ? 'bg-unknown-bg text-unknown' : 'bg-fill text-ink-2'
                        }`}
                      >
                        {aid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
