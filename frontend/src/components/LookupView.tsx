import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api'
import { catLabel, type Lang, type Strings } from '../lib/i18n'
import type { AddressHit, LookupAnswer, ResultItem } from '../lib/types'
import AuditPanel, { ChecksList } from './AuditPanel'
import EvidenceSheet from './EvidenceSheet'
import Landing, { StrataVisual } from './Landing'
import RightsSheet from './RightsSheet'
import { Card, ErrorNote, LayerTag, ResultBadge, Spinner } from './ui'

interface Props {
  s: Strings
  lang: Lang
  asOf: string
  selectedId: string | null
  onSelect: (id: string) => void
  initialRights?: boolean
  onRightsChange?: (open: boolean) => void
  onTimeMachine?: () => void
}

const RANK: Record<ResultItem['result'], number> = { applies: 0, unknown: 1, not_yet_effective: 2, pending: 3, superseded: 4 }

export default function LookupView({ s, lang, asOf, selectedId, onSelect, initialRights, onRightsChange, onTimeMachine }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [q, setQ] = useState('')
  const [focused, setFocused] = useState(false)
  const [hits, setHits] = useState<AddressHit[]>([])
  const [showAny, setShowAny] = useState(false)
  const [free, setFree] = useState({ address: '', year: '', units: '' })
  const [answer, setAnswer] = useState<LookupAnswer | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [evidence, setEvidence] = useState<string | null>(null)
  const [rights, setRightsState] = useState(!!initialRights)
  const setRights = (open: boolean) => {
    setRightsState(open)
    onRightsChange?.(open)
  }
  const [whatIf, setWhatIf] = useState<{ year?: number; units?: number } | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const id = setTimeout(() => {
      api<AddressHit[]>(`/addresses?limit=8&q=${encodeURIComponent(q)}`).then(setHits).catch(() => setHits([]))
    }, 120)
    return () => clearTimeout(id)
  }, [q])

  useEffect(() => {
    if (!selectedId || selectedId === 'live') return
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ address_id: selectedId, as_of: asOf })
    if (whatIf?.year) params.set('year_built', String(whatIf.year))
    if (whatIf?.units) params.set('units', String(whatIf.units))
    api<LookupAnswer>(`/lookup?${params}`)
      .then(setAnswer)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [selectedId, asOf, whatIf])

  useEffect(() => setWhatIf(null), [selectedId])

  useEffect(() => {
    const close = (e: MouseEvent) => boxRef.current && !boxRef.current.contains(e.target as Node) && setFocused(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const choose = (id: string) => {
    setFocused(false)
    setQ('')
    onSelect(id)
  }

  const runFree = () => {
    if (free.address.trim().length < 5) return
    const params = new URLSearchParams({ address: free.address, as_of: asOf })
    if (free.year) params.set('year_built', free.year)
    if (free.units) params.set('units', free.units)
    setLoading(true)
    setError(null)
    api<LookupAnswer>(`/lookup_free?${params}`)
      .then((a) => {
        setAnswer(a)
        onSelect('live')
      })
      .catch((e) => setError(String(e).replace(/^Error: \d+ /, '').replace(/^\{"detail":"|"\}$/g, '')))
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-10">
      <section
        className={
          answer
            ? 'mx-auto max-w-3xl pt-2 text-center'
            : 'relative -mt-10 grid min-h-[calc(100svh-6.5rem)] items-center gap-16 pb-24 pt-10 lg:grid-cols-[1.2fr_0.8fr]'
        }
      >
        <div className={answer ? '' : 'text-center lg:text-left'}>
        {!answer && (
          <>
            <p className="anim-fade-up eyebrow text-accent">{s.heroTitle}</p>
            <h1
              className="anim-fade-up mt-4 text-[48px] font-semibold leading-[1.02] tracking-[-0.04em] sm:text-[72px] xl:text-[80px]"
              style={{ animationDelay: '120ms' }}
            >
              {s.tagline.split('. ').map((part, i, arr) => (
                <span key={i} className="block">
                  {part}
                  {i < arr.length - 1 ? '.' : ''}
                </span>
              ))}
            </h1>
            <p
              className="anim-fade-up mx-auto mt-7 max-w-xl text-[20px] leading-relaxed text-muted lg:mx-0"
              style={{ animationDelay: '260ms' }}
            >
              {s.heroSub}
            </p>
          </>
        )}
        <div
          ref={boxRef}
          className={`relative text-left ${answer ? 'mx-auto max-w-2xl' : 'anim-fade-up mx-auto mt-12 max-w-xl lg:mx-0'}`}
          style={answer ? undefined : { animationDelay: '400ms' }}
        >
          <div className="flex items-center gap-3 rounded-2xl border border-hairline bg-white px-5 shadow-[0_2px_12px_rgba(0,0,0,0.05)] transition focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/15">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#86868b" strokeWidth="2.2" strokeLinecap="round">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              ref={inputRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onFocus={() => setFocused(true)}
              placeholder={s.searchPlaceholder}
              className="w-full bg-transparent py-4 text-[17px] placeholder:text-faint focus:outline-none"
            />
          </div>
          {focused && hits.length > 0 && (
            <ul className="absolute inset-x-0 top-[calc(100%+8px)] z-30 overflow-hidden rounded-2xl border border-hairline/60 bg-white/95 py-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.12)] backdrop-blur-xl">
              {hits.map((h) => (
                <li key={h.address_id}>
                  <button onClick={() => choose(h.address_id)} className="flex w-full items-center justify-between gap-4 px-5 py-2.5 text-left hover:bg-fill">
                    <span>
                      <span className="block text-[15px] font-medium">{h.street_address}</span>
                      <span className="block text-[13px] text-muted">{h.jurisdiction_city ?? `${h.postal_city}, ${h.state}`}</span>
                    </span>
                    <span className="shrink-0 text-[12px] tabular-nums text-faint">
                      {h.year_built ?? '—'} · {h.units ?? (h.units_min ? `${h.units_min}+` : '?')} units · {h.address_id}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {!answer && (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2 lg:justify-start">
              <span className="text-[13px] text-faint">{s.tryLabel}:</span>
              {s.examples.map((ex) => (
                <button
                  key={ex.id}
                  onClick={() => choose(ex.id)}
                  className="rounded-full border border-hairline bg-white px-3.5 py-1.5 text-[13px] font-medium text-ink-2 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition hover:border-accent hover:text-accent"
                >
                  {ex.label}
                </button>
              ))}
            </div>
          )}
          <div className={`mt-4 text-center ${answer ? '' : 'lg:-ml-3 lg:text-left'}`}>
            <button onClick={() => setShowAny(!showAny)} className="btn-ghost">
              {s.anyAddress} {showAny ? '↑' : '↓'}
            </button>
          </div>
          {showAny && (
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                value={free.address}
                onChange={(e) => setFree({ ...free, address: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && runFree()}
                placeholder={s.anyPlaceholder}
                className="field sm:flex-1"
              />
              <input
                value={free.year}
                onChange={(e) => setFree({ ...free, year: e.target.value.replace(/\D/g, '') })}
                placeholder={s.yearBuilt}
                className="field sm:w-24"
              />
              <input
                value={free.units}
                onChange={(e) => setFree({ ...free, units: e.target.value.replace(/\D/g, '') })}
                placeholder={s.units}
                className="field sm:w-24"
              />
              <button onClick={runFree} className="btn-primary">
                {s.go}
              </button>
            </div>
          )}
        </div>
        </div>
        {!answer && (
          <div className="relative hidden lg:block">
            <div className="pointer-events-none absolute left-1/2 top-1/2 h-[460px] w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(88,86,214,0.16),rgba(10,158,143,0.08)_45%,transparent_70%)]" />
            <div className="relative scale-[1.35]">
              <StrataVisual />
            </div>
          </div>
        )}
        {!answer && (
          <button
            onClick={() => document.getElementById('landing')?.scrollIntoView({ behavior: 'smooth' })}
            className="anim-fade-up absolute bottom-6 left-1/2 flex -translate-x-1/2 flex-col items-center gap-1 text-[12px] font-medium text-faint hover:text-ink"
            style={{ animationDelay: '1400ms' }}
          >
            {s.landing.scroll}
            <span className="anim-cue text-[18px]">↓</span>
          </button>
        )}
      </section>

      {!answer && !loading && (
        <div id="landing">
          <Landing
            s={s}
            onExample={choose}
            onTimeMachine={() => onTimeMachine?.()}
            onSearch={() => {
              window.scrollTo({ top: 0, behavior: 'smooth' })
              setTimeout(() => inputRef.current?.focus(), 500)
            }}
          />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {loading && <Spinner label={s.loading} />}
      {!loading && answer && (
        <AnswerPanel
          answer={answer}
          s={s}
          lang={lang}
          onEvidence={setEvidence}
          onRights={() => setRights(true)}
          whatIf={selectedId !== 'live' ? setWhatIf : undefined}
        />
      )}
      {evidence && <EvidenceSheet ruleId={evidence} s={s} onClose={() => setEvidence(null)} />}
      {rights && answer && (
        <div className="rights-host">
          <RightsSheet answer={answer} s={s} lang={lang} onClose={() => setRights(false)} />
        </div>
      )}
    </div>
  )
}

function AnswerPanel({
  answer,
  s,
  lang,
  onEvidence,
  onRights,
  whatIf,
}: {
  answer: LookupAnswer
  s: Strings
  lang: Lang
  onEvidence: (id: string) => void
  onRights: () => void
  whatIf?: (v: { year?: number; units?: number } | null) => void
}) {
  const a = answer.address
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState({ year: '', units: '' })
  const unknownN = answer.summary.unknown ?? 0
  const groups = useMemo(() => {
    const m = new Map<string, ResultItem[]>()
    for (const r of answer.results) m.set(r.category_label, [...(m.get(r.category_label) ?? []), r])
    return [...m.entries()].map(([label, items]) => {
      // Top stratum first: the governing local rule sits above the state rule it displaces.
      items.sort((x, y) => RANK[x.result] - RANK[y.result] || (x.level === 'city' ? -1 : 1))
      return [label, items] as const
    })
  }, [answer])

  return (
    <div className="space-y-6">
      <Card className="page-in p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">
              {a.address_id} · {s.asOf} {answer.as_of}
            </p>
            <h2 className="mt-1 text-[34px] font-semibold leading-tight tracking-[-0.02em]">{a.street_address}</h2>
            <p className="text-[17px] text-muted">
              {a.postal_city}, {a.state} {a.zip}
            </p>
          </div>
          <div className="flex flex-col items-end gap-3">
            <button onClick={onRights} className="btn-primary">
              {lang === 'es' ? 'Resumen para inquilinos' : 'Renter summary'}
            </button>
            <div className="flex flex-wrap justify-end gap-2">
            {(Object.entries(answer.summary) as [ResultItem['result'], number][])
              .sort((x, y) => RANK[x[0]] - RANK[y[0]])
              .map(([k, v]) => (
                <ResultBadge key={k} result={k} label={`${v} ${s.results[k]}`} title={s.tips[k]} />
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-6 border-t border-hairline/60 pt-6 sm:grid-cols-2">
          <div>
            <p className="eyebrow">{s.jurisdiction}</p>
            <div className="mt-3 space-y-1.5">
              {/* Legal city with no rules in the corpus (e.g. Emeryville behind an Oakland mailing address). */}
              {!answer.jurisdiction_stack.some((j) => j.includes(',') && !j.includes('County')) && a.census_place?.endsWith(' city') && (
                <div className="flex items-center justify-between rounded-xl border border-dashed border-layer-city/60 bg-layer-city/10 px-4 py-2.5 text-[15px] font-medium text-layer-city">
                  <span>
                    {a.census_place.replace(/ city$/, '')}, {a.state}
                  </span>
                  <span className="text-[12px] font-normal opacity-80">{s.cityNoRules}</span>
                </div>
              )}
              {[...answer.jurisdiction_stack].reverse().map((j) => {
                const isCounty = j.includes('County')
                const isCity = j.includes(',') && !isCounty
                const cls = isCity ? 'ml-0 bg-layer-city' : isCounty ? 'ml-3 bg-[#8e8e93]' : 'ml-6 bg-layer-state'
                return (
                  <div key={j} className={`flex items-center justify-between rounded-xl px-4 py-2.5 text-[15px] font-medium text-white ${cls}`}>
                    <span>{j.replace(/, (CA|NJ|MA)$/, isCity ? ', $1' : '')}</span>
                    <span className="text-[12px] font-normal opacity-80">
                      {isCity ? s.cityLayer : isCounty ? s.countyLayer : s.stateLayer}
                    </span>
                  </div>
                )
              })}
            </div>
            <p className="mt-2 text-[12px] text-faint">
              {a.census_place ? `Census place: ${a.census_place}` : a.resolution_method}
            </p>
          </div>
          <div>
            <p className="eyebrow">{s.building}</p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Fact big={a.year_built ? String(a.year_built) : '—'} small={a.year_built ? s.yearBuilt : s.yearUnknown} />
              <Fact
                big={a.units != null ? String(a.units) : a.units_min ? `${a.units_min}+` : '—'}
                small={a.units != null || a.units_min ? s.units : s.unitsUnknown}
              />
            </div>
            <p className="mt-2 text-[12px] text-faint">
              {a.units_basis}
              {a.use_description ? ` · ${a.use_description}` : ''}
            </p>
            {whatIf && !editing && (
              <button onClick={() => setEditing(true)} className="btn-ghost -ml-3 mt-1">
                {s.whatIf}
              </button>
            )}
            {whatIf && editing && (
              <div className="mt-3 rounded-2xl bg-fill p-3">
                <p className="text-[12px] text-muted">{s.whatIfHint}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <input
                    value={draft.year}
                    onChange={(e) => setDraft({ ...draft, year: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                    placeholder={s.yearBuilt}
                    className="field w-28 py-2 text-[14px]"
                  />
                  <input
                    value={draft.units}
                    onChange={(e) => setDraft({ ...draft, units: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                    placeholder={s.units}
                    className="field w-24 py-2 text-[14px]"
                  />
                  <button
                    onClick={() =>
                      whatIf({ year: draft.year ? Number(draft.year) : undefined, units: draft.units ? Number(draft.units) : undefined })
                    }
                    disabled={!draft.year && !draft.units}
                    className="btn-primary px-4 py-2 text-[13px]"
                  >
                    {s.whatIfApply}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {answer.what_if && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-future-bg px-5 py-3 text-[14px] text-future">
          <span>{s.whatIfBanner}</span>
          <button
            onClick={() => {
              whatIf?.(null)
              setEditing(false)
              setDraft({ year: '', units: '' })
            }}
            className="font-semibold hover:underline"
          >
            {s.whatIfReset}
          </button>
        </div>
      )}
      {!answer.what_if && unknownN > 0 && whatIf && (
        <p className="rounded-2xl bg-unknown-bg px-5 py-3 text-[14px] text-unknown">{s.unknownHint(unknownN)}</p>
      )}

      {groups.map(([label, items], gi) => (
        <Card key={label} className="stagger overflow-hidden" style={{ animationDelay: `${120 + gi * 70}ms` }}>
          <div className="flex items-center justify-between px-8 pb-2 pt-6">
            <h3 className="text-[21px] font-semibold tracking-tight">{catLabel(label, lang)}</h3>
            <ResultBadge result={items[0].result} label={s.results[items[0].result]} />
          </div>
          <div className="divide-y divide-hairline/60">
            {items.map((r) => (
              <RuleRow key={r.team_rule_id} r={r} s={s} lang={lang} onEvidence={onEvidence} />
            ))}
          </div>
        </Card>
      ))}

      {answer.categories_without_rules.length > 0 && (
        <Card className="px-8 py-6">
          <p className="text-[15px] font-medium text-ink-2">{s.noRule}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {answer.categories_without_rules.map((c) => (
              <span key={c.category} className="rounded-full bg-fill px-3 py-1 text-[13px] text-muted">
                {catLabel(c.category_label, lang)}
              </span>
            ))}
          </div>
          {answer.no_rule_findings.slice(0, 3).map((f, i) => (
            <p key={i} className="mt-3 text-[13px] leading-relaxed text-muted">
              <span className="font-medium text-ink-2">{f.jurisdiction}</span> · {f.finding}
            </p>
          ))}
        </Card>
      )}

      <p className="pb-4 text-center text-[12px] text-faint">{answer.disclaimer}</p>
    </div>
  )
}

function Fact({ big, small }: { big: string; small: string }) {
  return (
    <div className="rounded-2xl bg-fill px-4 py-3">
      <p className="text-[26px] font-semibold tabular-nums tracking-tight">{big}</p>
      <p className="text-[12px] text-muted">{small}</p>
    </div>
  )
}

function RuleRow({ r, s, lang, onEvidence }: { r: ResultItem; s: Strings; lang: Lang; onEvidence: (id: string) => void }) {
  const requirement = lang === 'es' && r.requirement_es ? r.requirement_es : r.requirement
  const title = lang === 'es' && r.title_es ? r.title_es : r.title
  const keyValue = lang === 'es' && r.key_value_es ? r.key_value_es : r.key_value
  const dim = r.result === 'superseded'
  const [audit, setAudit] = useState(false)
  return (
    <div className={`grid gap-4 px-8 py-6 sm:grid-cols-[1fr_auto] ${dim ? 'bg-[#fafafa]' : ''}`}>
      <div className={`min-w-0 ${dim ? 'opacity-60' : ''}`}>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <LayerTag level={r.level}>{r.jurisdiction}</LayerTag>
          <span className="text-[12px] text-faint">{r.citation}</span>
        </div>
        <p className="mt-1.5 text-[17px] font-semibold leading-snug tracking-tight">{title}</p>
        <p className="mt-1 text-[15px] leading-relaxed text-ink-2">{requirement}</p>
        <div className="mt-3">
          {r.result === 'superseded' || r.result === 'pending' || r.result === 'not_yet_effective' ? (
            <p className="text-[13px] leading-relaxed text-muted">
              <span className="font-semibold text-ink-2">{s.why}.</span> {r.explanation}
            </p>
          ) : (
            <ChecksList checks={r.audit.checks} />
          )}
        </div>
        {r.conflict_flag && (
          <p className="mt-3 rounded-xl bg-unknown-bg px-3.5 py-2.5 text-[13px] leading-relaxed text-unknown">
            <span className="font-semibold">{s.conflict}.</span> {r.conflict_note || r.interaction || s.conflictDefault}
          </p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
          <button onClick={() => onEvidence(r.team_rule_id)} className="btn-ghost -ml-3">
            {s.source} →
          </button>
          <button onClick={() => setAudit(!audit)} className="btn-ghost -ml-3">
            {audit ? s.audit.close : s.audit.open} {audit ? '↑' : '↓'}
          </button>
          {r.effective_date && (
            <span className="text-[12px] text-faint">
              {s.effective} {r.effective_date}
            </span>
          )}
          <span className="text-[12px] text-faint">
            {s.confidence} {r.confidence ?? '—'}
          </span>
        </div>
        {audit && <AuditPanel audit={r.audit} penalty={r.penalty} s={s} onSource={() => onEvidence(r.team_rule_id)} />}
      </div>
      <div className="flex flex-row items-start gap-3 sm:flex-col sm:items-end">
        <ResultBadge result={r.result} label={s.results[r.result]} title={s.tips[r.result]} />
        {keyValue && <p className="max-w-[220px] text-[15px] font-semibold leading-snug sm:text-right">{keyValue}</p>}
      </div>
    </div>
  )
}

