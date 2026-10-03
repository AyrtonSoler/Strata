import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import type { Rule } from '../lib/types'
import CoverageMatrix from './CoverageMatrix'
import EvidenceSheet from './EvidenceSheet'
import { Card, ErrorNote, Spinner } from './ui'

const STATUS: Record<string, { cls: string; label: string }> = {
  in_force: { cls: 'bg-applies-bg text-applies', label: 'In force' },
  not_yet_effective: { cls: 'bg-future-bg text-future', label: 'Not yet effective' },
  pending: { cls: 'bg-pending-bg text-pending', label: 'Pending' },
  failed: { cls: 'bg-superseded-bg text-superseded', label: 'Failed' },
}
const STATE_NAME: Record<string, string> = { CA: 'California', NJ: 'New Jersey', MA: 'Massachusetts' }
const stateOf = (j: string) => (j.includes(',') ? j.split(', ')[1] : j)

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-[13px] font-medium transition ${
        active ? 'bg-ink text-white' : 'bg-white text-ink-2 ring-1 ring-hairline hover:ring-ink/30'
      }`}
    >
      {children}
    </button>
  )
}

function ConfidenceBar({ value }: { value: number | null }) {
  const v = Math.round((value ?? 0) * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-hairline">
        <div className="h-full rounded-full bg-accent" style={{ width: `${v}%` }} />
      </div>
      <span className="w-8 text-right text-[11px] tabular-nums text-faint">{value ?? '—'}</span>
    </div>
  )
}

function RuleRow({ r, categories, s, open, onToggle, onSource }: {
  r: Rule
  categories: Record<string, string>
  s: Strings
  open: boolean
  onToggle: () => void
  onSource: () => void
}) {
  const st = STATUS[r.status] ?? { cls: 'bg-fill text-muted', label: r.status }
  const v = r.verification
  return (
    <li className={`transition-colors ${open ? 'bg-fill/60' : 'hover:bg-fill/40'}`}>
      <button onClick={onToggle} className="grid w-full items-center gap-x-6 gap-y-2 px-6 py-4 text-left md:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)_auto]">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">{categories[r.category]}</p>
          <p className="mt-0.5 truncate text-[15px] font-semibold tracking-tight">{r.title}</p>
          <p className="truncate text-[12px] text-faint">{r.citation}</p>
        </div>
        <p className="line-clamp-2 text-[13px] leading-relaxed text-ink-2">{r.requirement}</p>
        <div className="flex items-center gap-4 md:flex-col md:items-end md:gap-1.5">
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${st.cls}`}>
            {st.label}
            {r.conflict_flag ? ' ⚠' : ''}
          </span>
          <span className="text-[11px] tabular-nums text-faint">{r.effective_date ?? 'no date'}</span>
          <ConfidenceBar value={r.confidence} />
        </div>
      </button>
      {open && (
        <div className="expand grid gap-6 px-6 pb-6 md:grid-cols-2">
          <div className="space-y-3 text-[13px] leading-relaxed text-ink-2">
            <p className="text-[14px]">{r.requirement}</p>
            {r.key_value && (
              <p>
                <span className="font-semibold">Key value.</span> {r.key_value}
              </p>
            )}
            {r.coverage_conditions && (
              <p>
                <span className="font-semibold">Coverage.</span> {r.coverage_conditions}
              </p>
            )}
            {r.exemptions && (
              <p>
                <span className="font-semibold">Exemptions.</span> {r.exemptions}
              </p>
            )}
            {r.penalty && (
              <p>
                <span className="font-semibold">Penalty.</span> {r.penalty}
              </p>
            )}
            {r.interaction && (
              <p>
                <span className="font-semibold">Interaction.</span> {r.interaction}
              </p>
            )}
            {r.conflict_note && <p className="rounded-xl bg-unknown-bg px-3 py-2 text-unknown">⚠ {r.conflict_note}</p>}
          </div>
          <div className="space-y-3">
            <blockquote className="rounded-2xl bg-white p-4 text-[13px] italic leading-relaxed text-ink-2 ring-1 ring-hairline/70">“{r.quoted_span}”</blockquote>
            <div className="flex flex-wrap items-center gap-2 text-[11px]">
              <span className={`rounded-full px-2 py-0.5 font-semibold ${r.source_origin === 'starter_corpus' ? 'bg-applies-bg text-applies' : 'bg-unknown-bg text-unknown'}`}>
                {r.source_origin === 'starter_corpus' ? 'Official corpus' : 'Secondary source'}
              </span>
              {r.extraction_origins && r.extraction_origins.length > 1 && (
                <span className="rounded-full bg-accent/10 px-2 py-0.5 font-semibold text-accent">Found by both passes</span>
              )}
              {v?.verdict && (
                <span className={`rounded-full px-2 py-0.5 font-semibold ${v.verdict === 'pass' ? 'bg-applies-bg text-applies' : 'bg-unknown-bg text-unknown'}`}>
                  Verifier: {v.verdict}
                </span>
              )}
              <span className="text-faint">
                {r.source_doc_id} · {s.retrieved} {r.retrieved_at} · {r.team_rule_id}
              </span>
            </div>
            {v?.review_reasons && v.review_reasons.length > 0 && (
              <p className="text-[12px] text-unknown">Needs review: {v.review_reasons.join('; ')}</p>
            )}
            <button onClick={onSource} className="btn-ghost -ml-3">
              {s.source} →
            </button>
          </div>
        </div>
      )}
    </li>
  )
}

export default function RulesView({ s, categories }: { s: Strings; categories: Record<string, string> }) {
  const [rules, setRules] = useState<Rule[] | null>(null)
  const [grid, setGrid] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [state, setState] = useState('')
  const [jur, setJur] = useState('')
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [evidence, setEvidence] = useState<string | null>(null)

  useEffect(() => {
    api<{ rules: Rule[]; coverage_grid: Record<string, string> }>('/rules')
      .then((d) => {
        setRules(d.rules)
        setGrid(d.coverage_grid ?? {})
      })
      .catch((e) => setError(String(e)))
  }, [])

  const shown = useMemo(() => {
    const ql = q.toLowerCase().trim()
    return (rules ?? []).filter(
      (r) =>
        (!state || stateOf(r.jurisdiction) === state) &&
        (!jur || r.jurisdiction === jur) &&
        (!cat || r.category === cat) &&
        (!ql || `${r.title} ${r.citation} ${r.requirement} ${r.jurisdiction}`.toLowerCase().includes(ql)),
    )
  }, [rules, state, jur, cat, q])

  const groups = useMemo(() => {
    const m = new Map<string, Rule[]>()
    for (const r of shown) m.set(r.jurisdiction, [...(m.get(r.jurisdiction) ?? []), r])
    return [...m.entries()]
  }, [shown])

  if (error) return <ErrorNote message={error} />
  if (!rules) return <Spinner label={s.loading} />

  const both = rules.filter((r) => (r.extraction_origins ?? []).length > 1).length
  const verified = rules.filter((r) => r.verification?.verdict === 'pass').length
  const jurisdictions = new Set(rules.map((r) => r.jurisdiction)).size
  const anyFilter = state || jur || cat || q

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <section className="pt-6 text-center">
        <p className="page-in eyebrow text-accent">{s.tabRules}</p>
        <h1 className="page-in mt-3 text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[56px]" style={{ animationDelay: '80ms' }}>
          Read from the law itself.
        </h1>
        <p className="page-in mx-auto mt-4 max-w-xl text-[19px] leading-snug text-muted" style={{ animationDelay: '160ms' }}>
          Every rule was extracted automatically and is tied to a quote verified against its source.
        </p>
      </section>

      <Card className="page-in grid grid-cols-2 divide-hairline/60 md:grid-cols-4 md:divide-x" style={{ animationDelay: '220ms' }}>
        {[
          [String(rules.length), 'rules extracted'],
          [String(jurisdictions), 'jurisdictions'],
          [`${both}/${rules.length}`, 'found by both AI passes'],
          [`${verified}/${rules.length}`, 'passed the verifier'],
        ].map(([n, label]) => (
          <div key={label} className="px-6 py-6 text-center">
            <p className="text-[34px] font-semibold leading-none tabular-nums tracking-tight">{n}</p>
            <p className="mt-2 text-[13px] text-muted">{label}</p>
          </div>
        ))}
      </Card>

      {Object.keys(grid).length > 0 && (
        <CoverageMatrix
          grid={grid}
          rules={rules}
          categories={categories}
          onPick={(j, c) => {
            setState('')
            setJur(j)
            setCat(c)
            setTimeout(() => document.getElementById('rule-list')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
          }}
        />
      )}

      <div id="rule-list" className="scroll-mt-24 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {['', 'CA', 'NJ', 'MA'].map((st) => (
            <Chip
              key={st || 'all'}
              active={state === st && !jur}
              onClick={() => {
                setState(st)
                setJur('')
              }}
            >
              {st ? STATE_NAME[st] : 'All states'}
            </Chip>
          ))}
          <div className="ml-auto flex items-center gap-2 rounded-full bg-white px-4 ring-1 ring-hairline focus-within:ring-accent">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#86868b" strokeWidth="2.4" strokeLinecap="round">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search citation or title" className="w-52 bg-transparent py-1.5 text-[13px] focus:outline-none" />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Chip active={!cat} onClick={() => setCat('')}>
            All categories
          </Chip>
          {Object.entries(categories).map(([k, v]) => (
            <Chip key={k} active={cat === k} onClick={() => setCat(k)}>
              {v}
            </Chip>
          ))}
        </div>
        <div className="flex items-center justify-between text-[13px] text-muted">
          <span>
            {shown.length} {shown.length === 1 ? 'rule' : 'rules'}
            {jur ? ` in ${jur}` : ''}
          </span>
          {anyFilter && (
            <button
              onClick={() => {
                setState('')
                setJur('')
                setCat('')
                setQ('')
              }}
              className="btn-ghost"
            >
              Clear filters
            </button>
          )}
        </div>

        {groups.map(([j, list], gi) => (
          <Card key={j} className="stagger overflow-hidden" style={{ animationDelay: `${Math.min(gi, 8) * 60}ms` }}>
            <div className="flex items-center justify-between border-b border-hairline/60 px-6 py-3.5">
              <p className="flex items-center gap-2.5 text-[15px] font-semibold">
                <span className={`h-2.5 w-2.5 rounded-[3px] ${j.includes(',') ? 'bg-layer-city' : 'bg-layer-state'}`} />
                {j.includes(',') ? j : STATE_NAME[j] ?? j}
                <span className="text-[12px] font-normal text-faint">{j.includes(',') ? 'City' : 'State'}</span>
              </p>
              <span className="text-[12px] tabular-nums text-faint">{list.length}</span>
            </div>
            <ul className="divide-y divide-hairline/50">
              {list.map((r) => (
                <RuleRow
                  key={r.team_rule_id}
                  r={r}
                  categories={categories}
                  s={s}
                  open={open === r.team_rule_id}
                  onToggle={() => setOpen(open === r.team_rule_id ? null : r.team_rule_id)}
                  onSource={() => setEvidence(r.team_rule_id)}
                />
              ))}
            </ul>
          </Card>
        ))}
        {groups.length === 0 && <p className="py-10 text-center text-[14px] text-muted">No rules match these filters.</p>}
      </div>
      {evidence && <EvidenceSheet ruleId={evidence} s={s} onClose={() => setEvidence(null)} />}
    </div>
  )
}
