import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import { Card, ErrorNote, Spinner } from './ui'

interface Audit {
  events: Record<string, unknown>[]
  llm: { usd?: number; calls?: number; input_tokens?: number; output_tokens?: number }
}

const STEPS = [
  ['Extract', 'Claude reads each source document and returns rule records in the official schema. Every quote is checked character by character against the source; unverifiable quotes are rejected.'],
  ['Reconcile', 'Descriptions of the same law from different sources are merged. Official text wins over secondary pages. Preemption and conflicting dates are flagged for human review.'],
  ['Resolve', 'Each address goes through the Census Geocoder to its legal city, not its postal one. Van Nuys is Los Angeles; Dorchester is Boston.'],
  ['Apply', 'Plain code tests each rule’s coverage: units, certificate-of-occupancy cutoffs, rolling exemptions, owner-type exemptions. Missing facts mean “unknown,” never a guess.'],
  ['Track', 'Everything is recomputed for any date. Amendments keep their prior version in force; pending bills and struck measures are never reported as law.'],
]

export default function AuditView({ s }: { s: Strings }) {
  const [data, setData] = useState<Audit | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api<Audit>('/audit').then(setData).catch((e) => setError(String(e)))
  }, [])
  if (error) return <ErrorNote message={error} />
  if (!data) return <Spinner label={s.loading} />
  return (
    <div className="space-y-10">
      <section className="mx-auto max-w-3xl pt-6 text-center">
        <h1 className="text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[52px]">AI reads. Code decides.</h1>
        <p className="mx-auto mt-3 max-w-xl text-[19px] leading-snug text-muted">
          The model extracts rules from legal text. Deterministic code applies them, so every answer is reproducible and auditable.
        </p>
      </section>
      <div className="grid gap-4 md:grid-cols-5">
        {STEPS.map(([title, body], i) => (
          <Card key={title} className="p-6">
            <p className="text-[13px] font-semibold tabular-nums text-accent">0{i + 1}</p>
            <p className="mt-1 text-[19px] font-semibold tracking-tight">{title}</p>
            <p className="mt-2 text-[13px] leading-relaxed text-muted">{body}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ['LLM calls', (data.llm.calls ?? 0).toLocaleString()],
          ['Input tokens', (data.llm.input_tokens ?? 0).toLocaleString()],
          ['Output tokens', (data.llm.output_tokens ?? 0).toLocaleString()],
        ].map(([k, v]) => (
          <Card key={k} className="p-6 text-center">
            <p className="text-[34px] font-semibold tabular-nums tracking-tight">{v}</p>
            <p className="text-[13px] text-muted">{k}</p>
          </Card>
        ))}
      </div>
      <Card className="overflow-hidden">
        <div className="px-7 pb-3 pt-6">
          <h3 className="text-[19px] font-semibold tracking-tight">Audit log</h3>
          <p className="text-[13px] text-muted">Every model call, rejected quote and merge decision.</p>
        </div>
        <div className="max-h-[480px] overflow-auto border-t border-hairline/60">
          <table className="min-w-full text-left text-[12px]">
            <tbody className="divide-y divide-hairline/50">
              {data.events.map((e, i) => (
                <tr key={i} className="align-top">
                  <td className="whitespace-nowrap px-7 py-2 font-semibold text-ink-2">{String(e.event)}</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted">
                    {Object.entries(e)
                      .filter(([k]) => k !== 'event' && k !== 'cost_usd')
                      .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
                      .join('  ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
