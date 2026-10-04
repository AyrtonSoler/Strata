import { useCallback, useEffect, useState } from 'react'
import AuditView from './components/AuditView'
import ChangesView from './components/ChangesView'
import LookupView from './components/LookupView'
import RulesView from './components/RulesView'
import TimeMachine, { type TimeState } from './components/TimeMachine'
import { DatePicker } from './components/controls'
import { Segmented, StrataMark } from './components/ui'
import { api } from './lib/api'
import { t, type Lang } from './lib/i18n'
import type { Meta } from './lib/types'

type Tab = 'lookup' | 'time' | 'changes' | 'rules' | 'audit'
const TABS: Tab[] = ['lookup', 'time', 'changes', 'rules', 'audit']
const DEFAULT_AS_OF = '2026-10-01'

// Shareable links: the URL carries the view, e.g. ?a=A0016&asOf=2027-07-02&lang=es
// or ?tab=time&date=2026-01-02&lens=algorithmic_rent_setting&region=CA
const initial = new URLSearchParams(window.location.search)

export default function App() {
  const [lang, setLang] = useState<Lang>(initial.get('lang') === 'es' ? 'es' : 'en')
  const [tab, setTab] = useState<Tab>(TABS.includes(initial.get('tab') as Tab) ? (initial.get('tab') as Tab) : 'lookup')
  const [meta, setMeta] = useState<Meta | null>(null)
  const [asOf, setAsOf] = useState(initial.get('asOf') || DEFAULT_AS_OF)
  const [selected, setSelected] = useState<string | null>(initial.get('a'))
  const [rights, setRights] = useState(initial.get('rights') === '1')
  const [timeState, setTimeState] = useState<TimeState | null>(null)
  const onTimeChange = useCallback((st: TimeState) => setTimeState(st), [])
  const s = t(lang)

  useEffect(() => {
    api<Meta>('/meta')
      .then((m) => {
        setMeta(m)
        if (!initial.get('asOf')) setAsOf(m.default_as_of)
      })
      .catch(() => setMeta(null))
  }, [])

  useEffect(() => {
    const q = new URLSearchParams()
    if (tab !== 'lookup') q.set('tab', tab)
    if (tab === 'lookup' && selected && selected !== 'live') q.set('a', selected)
    if (tab === 'lookup' && asOf !== DEFAULT_AS_OF) q.set('asOf', asOf)
    if (tab === 'lookup' && rights && selected) q.set('rights', '1')
    if (tab === 'time' && timeState) {
      q.set('date', timeState.date)
      q.set('lens', timeState.lens)
      q.set('region', timeState.region)
    }
    if (lang === 'es') q.set('lang', 'es')
    const url = `${window.location.pathname}${q.toString() ? `?${q}` : ''}`
    window.history.replaceState(null, '', url)
  }, [tab, selected, asOf, rights, timeState, lang])

  const openAddress = (id: string) => {
    setSelected(id)
    setTab('lookup')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const tabs: [Tab, string][] = [
    ['lookup', s.tabLookup],
    ['time', s.tabTime],
    ['changes', s.tabChanges],
    ['rules', s.tabRules],
    ['audit', s.tabAudit],
  ]

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-[900] border-b border-black/[0.06]">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-6 px-5">
          <button onClick={() => setTab('lookup')} className="flex items-center gap-2">
            <StrataMark size={26} />
            <span className="text-[19px] font-semibold tracking-[-0.02em]">{s.brand}</span>
          </button>
          <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
            {tabs.map(([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`rounded-full px-3.5 py-1.5 text-[13px] font-medium transition ${
                  tab === id ? 'bg-ink text-white' : 'text-ink-2 hover:bg-black/5'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 md:ml-0">
            {tab === 'lookup' && (
              <div className="hidden items-center gap-2 text-[13px] text-muted sm:flex">
                {s.asOf}
                <DatePicker
                  value={asOf}
                  onChange={setAsOf}
                  lang={lang}
                  min="2024-01-01"
                  max="2028-12-31"
                  presets={[
                    ['2026-10-01', lang === 'es' ? 'Fecha base' : 'Default date'],
                    ['2025-12-31', 'Dec 31, 2025'],
                    ['2026-01-02', 'Jan 2, 2026'],
                    ['2027-07-02', 'Jul 2, 2027'],
                  ]}
                />
              </div>
            )}
            <Segmented
              size="sm"
              value={lang}
              onChange={setLang}
              options={[
                ['en', 'EN'],
                ['es', 'ES'],
              ]}
            />
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`whitespace-nowrap rounded-full px-3 py-1 text-[13px] font-medium ${tab === id ? 'bg-ink text-white' : 'text-ink-2'}`}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <div className="border-b border-black/[0.04] bg-[#fbfbfd] py-2 text-center text-[12px] text-muted">{s.disclaimer}</div>

      <main key={tab} className="page-in mx-auto min-h-[72vh] max-w-[1200px] px-5 py-10">
        {tab === 'lookup' && (
          <LookupView
            s={s}
            lang={lang}
            asOf={asOf}
            selectedId={selected}
            onSelect={setSelected}
            initialRights={rights}
            onRightsChange={setRights}
            onTimeMachine={() => {
              setTab('time')
              window.scrollTo({ top: 0 })
            }}
          />
        )}
        {tab === 'time' && (
          <TimeMachine
            s={s}
            categories={meta?.categories ?? {}}
            onOpenAddress={openAddress}
            initial={{
              date: initial.get('date') ?? undefined,
              lens: initial.get('lens') ?? undefined,
              region: (initial.get('region') ?? undefined) as TimeState['region'] | undefined,
            }}
            onChange={onTimeChange}
          />
        )}
        {tab === 'changes' && <ChangesView s={s} onOpenAddress={openAddress} />}
        {tab === 'rules' && <RulesView s={s} categories={meta?.categories ?? {}} />}
        {tab === 'audit' && <AuditView s={s} />}
      </main>

      <footer className="border-t border-black/[0.06] bg-[#fbfbfd]">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-5 py-6 text-[12px] text-faint">
          <span className="flex items-center gap-2">
            <StrataMark size={16} /> Strata · Hack-Nation 7 · Challenge 2
          </span>
          <span>
            {meta ? `${meta.n_rules} rules · ${meta.n_addresses} properties · ` : ''}Public data only · Census Geocoder · RealPage starter corpus
          </span>
        </div>
      </footer>
    </div>
  )
}
