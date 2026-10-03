import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import type { Rule } from '../lib/types'
import CoverageMatrix from './CoverageMatrix'
import EvidenceSheet from './EvidenceSheet'
import { Card, ErrorNote, LayerTag, Spinner } from './ui'

const STATUS: Record<string, string> = {
  in_force: 'bg-applies-bg text-applies',
  not_yet_effective: 'bg-future-bg text-future',
  pending: 'bg-pending-bg text-pending',
  failed: 'bg-superseded-bg text-superseded',
}

export default function RulesView({ s, categories }: { s: Strings; categories: Record<string, string> }) {
  const [rules, setRules] = useState<Rule[] | null>(null)
  const [grid, setGrid] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [jur, setJur] = useState('')
  const [cat, setCat] = useState('')
  const [evidence, setEvidence] = useState<string | null>(null)

  useEffect(() => {
    api<{ rules: Rule[]; coverage_grid: Record<string, string> }>('/rules')
      .then((d) => {
        setRules(d.rules)
        setGrid(d.coverage_grid ?? {})
      })
      .catch((e) => setError(String(e)))
  }, [])

  const jurisdictions = useMemo(() => [...new Set((rules ?? []).map((r) => r.jurisdiction))], [rules])
  const shown = (rules ?? []).filter((r) => (!jur || r.jurisdiction === jur) && (!cat || r.category === cat))

  if (error) return <ErrorNote message={error} />
  if (!rules) return <Spinner label={s.loading} />

  return (
    <div className="space-y-8">
      <section className="mx-auto max-w-3xl pt-6 text-center">
        <h1 className="text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[52px]">Read from the law itself.</h1>
        <p className="mx-auto mt-3 max-w-xl text-[19px] leading-snug text-muted">
          {rules.length} rules extracted automatically from {new Set(rules.map((r) => r.source_doc_id)).size} source documents. Every one is tied to a verified quote.
        </p>
      </section>
      {Object.keys(grid).length > 0 && (
        <CoverageMatrix
          grid={grid}
          rules={rules}
          categories={categories}
          onPick={(j, c) => {
            setJur(j)
            setCat(c)
          }}
        />
      )}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <select value={jur} onChange={(e) => setJur(e.target.value)} className="field w-auto py-2 text-[14px]">
          <option value="">All jurisdictions</option>
          {jurisdictions.map((j) => (
            <option key={j}>{j}</option>
          ))}
        </select>
        <select value={cat} onChange={(e) => setCat(e.target.value)} className="field w-auto py-2 text-[14px]">
          <option value="">All categories</option>
          {Object.entries(categories).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <span className="px-2 text-[13px] text-muted">{shown.length} rules</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {shown.map((r) => (
          <Card key={r.team_rule_id} className="flex flex-col p-6">
            <div className="flex items-center justify-between gap-3">
              <LayerTag level={r.level as 'state' | 'city'}>{r.jurisdiction}</LayerTag>
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${STATUS[r.status] ?? ''}`}>{r.status.replace(/_/g, ' ')}</span>
            </div>
            <p className="mt-2 text-[12px] text-faint">
              {categories[r.category]} · {r.citation}
            </p>
            <p className="mt-1 text-[16px] font-semibold leading-snug tracking-tight">{r.title}</p>
            <p className="mt-1 text-[14px] leading-relaxed text-ink-2">{r.requirement}</p>
            {r.key_value && <p className="mt-2 text-[14px] font-semibold">{r.key_value}</p>}
            {r.conflict_flag && r.conflict_note && <p className="mt-3 rounded-xl bg-unknown-bg px-3 py-2 text-[12px] text-unknown">{r.conflict_note}</p>}
            <div className="mt-auto flex items-center justify-between pt-4">
              <button onClick={() => setEvidence(r.team_rule_id)} className="btn-ghost -ml-3">
                {s.source} →
              </button>
              <span className="text-[11px] text-faint">
                {r.team_rule_id} · {r.effective_date ?? 'no date'} · {s.confidence} {r.confidence ?? '—'}
              </span>
            </div>
          </Card>
        ))}
      </div>
      {evidence && <EvidenceSheet ruleId={evidence} s={s} onClose={() => setEvidence(null)} />}
    </div>
  )
}
