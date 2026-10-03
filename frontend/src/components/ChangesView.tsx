import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import type { ChangeTest, Result } from '../lib/types'
import { Card, ErrorNote, ResultBadge, Spinner } from './ui'

const TYPE_LABEL: Record<string, string> = {
  as_of: 'Effective-date change',
  boundary: 'Jurisdiction boundary',
  pending: 'Pending legislation',
  negative: 'Struck measure',
}

// One stable color per city, grouped by state family.
const CITY_COLOR: Record<string, string> = {
  'Los Angeles, CA': '#0a84ff',
  'San Francisco, CA': '#5e5ce6',
  'San Diego, CA': '#64d2ff',
  'Berkeley, CA': '#30b0c7',
  'Oakland, CA': '#40c8e0',
  'Jersey City, NJ': '#ff9f0a',
  'Hoboken, NJ': '#ffcc00',
  'Newark, NJ': '#ff6961',
  'Boston, MA': '#30d158',
  'Cambridge, MA': '#a2d729',
}
const short = (c: string) => c.replace(/, (CA|NJ|MA)$/, '')
const fmt = (iso?: string) =>
  iso ? new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }) : ''

function Transition({ c, s }: { c: ChangeTest; s: Strings }) {
  const t = c.transition
  if (t.kind === 'as_of') {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <ResultBadge result={t.from as Result} label={s.results[t.from as Result] ?? t.from} />
        <span className="flex items-center gap-2 text-[12px] tabular-nums text-muted">
          {fmt(t.from_date)}
          <span className="relative h-px w-16 bg-hairline sm:w-24">
            <span className="absolute -right-1 -top-[4px] text-[10px] text-faint">▶</span>
          </span>
          {fmt(t.to_date)}
        </span>
        <ResultBadge result={t.to as Result} label={s.results[t.to as Result] ?? t.to} />
      </div>
    )
  }
  if (t.kind === 'boundary') {
    return (
      <div className="flex flex-wrap gap-2">
        {t.rules?.map((r) => (
          <span
            key={r.jurisdiction}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold ${
              r.count > 0 ? 'bg-applies-bg text-applies' : 'bg-fill text-muted'
            }`}
          >
            {r.count > 0 ? '✓' : '✕'} {short(r.jurisdiction)}
            <span className="font-normal opacity-70">{r.count}</span>
          </span>
        ))}
      </div>
    )
  }
  if (t.kind === 'pending') {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <ResultBadge result="pending" label={s.results.pending} />
        <span className="text-[12px] text-muted">if enacted →</span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-applies/50 px-2.5 py-1 text-[12px] font-semibold text-applies">
          {s.results.applies}
        </span>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="rounded-full bg-superseded-bg px-2.5 py-1 text-[12px] font-semibold text-superseded">Failed</span>
      <span className="text-[12px] text-muted">→ never reported as law</span>
    </div>
  )
}

function CityBar({ byCity, total }: { byCity: Record<string, number>; total: number }) {
  const entries = Object.entries(byCity)
  if (!total) {
    return <div className="h-2.5 rounded-full bg-fill" />
  }
  return (
    <>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-fill">
        {entries.map(([city, n]) => (
          <span key={city} className="h-full transition-all" style={{ width: `${(n / total) * 100}%`, background: CITY_COLOR[city] ?? '#a1a1a6' }} title={`${city}: ${n}`} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {entries.map(([city, n]) => (
          <span key={city} className="flex items-center gap-1.5 text-[12px] text-muted">
            <span className="h-2 w-2 rounded-full" style={{ background: CITY_COLOR[city] ?? '#a1a1a6' }} />
            {short(city)} <span className="tabular-nums text-ink-2">{n}</span>
          </span>
        ))}
      </div>
    </>
  )
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

  const total = tests.reduce((n, c) => n + c.affected_address_ids.length, 0)
  const flagged = tests.reduce((n, c) => n + c.conflict_flag_address_ids.length, 0)
  const matches = tests.filter((c) => c.check?.matches).length

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <section className="pt-6 text-center">
        <p className="page-in eyebrow text-accent">{s.tabChanges}</p>
        <h1 className="page-in mt-3 text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[56px]" style={{ animationDelay: '80ms' }}>
          What changes, for whom.
        </h1>
        <p className="page-in mx-auto mt-4 max-w-xl text-[19px] leading-snug text-muted" style={{ animationDelay: '160ms' }}>
          The five supplied change cases, applied to every sample address. Pending bills stay pending; struck measures never count.
        </p>
      </section>

      <Card className="page-in grid grid-cols-2 divide-hairline/60 md:grid-cols-4 md:divide-x" style={{ animationDelay: '220ms' }}>
        {[
          [String(tests.length), 'change cases'],
          [`${matches}/${tests.length}`, 'match the expected behavior'],
          [String(total), 'address-level changes'],
          [String(flagged), 'flagged for human review'],
        ].map(([n, label]) => (
          <div key={label} className="px-6 py-6 text-center">
            <p className="text-[34px] font-semibold leading-none tabular-nums tracking-tight">{n}</p>
            <p className="mt-2 text-[13px] text-muted">{label}</p>
          </div>
        ))}
      </Card>

      <ol className="space-y-4">
        {tests.map((c, i) => {
          const id = c.test.test_id
          const n = c.affected_address_ids.length
          const flaggedSet = new Set(c.conflict_flag_address_ids)
          const isOpen = open === id
          return (
            <li key={id} className="stagger" style={{ animationDelay: `${300 + i * 90}ms` }}>
              <Card className="p-7">
                <div className="grid gap-6 md:grid-cols-[1fr_180px]">
                  <div className="min-w-0 space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="rounded-lg bg-ink px-2 py-0.5 text-[12px] font-bold tabular-nums text-white">{id}</span>
                      <span className="eyebrow">{TYPE_LABEL[c.test.type ?? ''] ?? c.test.type}</span>
                    </div>
                    <h3 className="text-[22px] font-semibold leading-snug tracking-tight">{c.test.title ?? id}</h3>
                    <Transition c={c} s={s} />
                    <CityBar byCity={c.by_city} total={n} />
                    {c.conflict_flag_address_ids.length > 0 && (
                      <p className="inline-flex rounded-full bg-unknown-bg px-3 py-1 text-[12px] font-semibold text-unknown">
                        ⚠ {c.conflict_flag_address_ids.length} flagged for possible preemption ·{' '}
                        {Object.keys(c.flagged_by_city).map(short).join(', ')}
                      </p>
                    )}
                    {c.test.expected_behavior && (
                      <p className="text-[13px] leading-relaxed text-muted">
                        <span className="font-semibold text-ink-2">{s.expected}.</span> {c.test.expected_behavior}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-row items-center justify-between gap-4 border-t border-hairline/60 pt-4 md:flex-col md:items-end md:justify-start md:border-0 md:pt-0">
                    <div className="md:text-right">
                      <p className="text-[52px] font-semibold leading-none tabular-nums tracking-[-0.04em]">{n}</p>
                      <p className="mt-1 text-[13px] text-muted">{s.affected} addresses</p>
                    </div>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold ${
                        c.check?.matches ? 'bg-applies-bg text-applies' : 'bg-unknown-bg text-unknown'
                      }`}
                    >
                      {c.check?.matches ? '✓ Matches expected' : 'Review'}
                    </span>
                  </div>
                </div>

                {n > 0 && (
                  <div className="mt-5 border-t border-hairline/60 pt-4">
                    <button onClick={() => setOpen(isOpen ? null : id)} className="btn-ghost -ml-3">
                      {isOpen ? 'Hide addresses ↑' : 'Show addresses ↓'}
                    </button>
                    {isOpen && (
                      <div className="expand mt-3 space-y-3">
                        {Object.entries(c.groups).map(([city, ids]) => (
                          <div key={city}>
                            <p className="mb-1.5 flex items-center gap-2 text-[12px] font-semibold text-ink-2">
                              <span className="h-2 w-2 rounded-full" style={{ background: CITY_COLOR[city] ?? '#a1a1a6' }} />
                              {city} · {ids.length}
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {ids.map((aid) => (
                                <button
                                  key={aid}
                                  onClick={() => onOpenAddress(aid)}
                                  className={`rounded-md px-2 py-0.5 font-mono text-[11px] transition hover:ring-2 hover:ring-accent/40 ${
                                    flaggedSet.has(aid) ? 'bg-unknown-bg text-unknown' : 'bg-fill text-ink-2'
                                  }`}
                                >
                                  {aid}
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
