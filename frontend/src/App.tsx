import { useEffect, useState } from 'react'
import AuditView from './components/AuditView'
import ChangesView from './components/ChangesView'
import LookupView from './components/LookupView'
import RulesView from './components/RulesView'
import TimeMachine from './components/TimeMachine'
import { Segmented, StrataMark } from './components/ui'
import { api } from './lib/api'
import { t, type Lang } from './lib/i18n'
import type { Meta } from './lib/types'

type Tab = 'lookup' | 'time' | 'changes' | 'rules' | 'audit'

export default function App() {
  const [lang, setLang] = useState<Lang>('en')
  const [tab, setTab] = useState<Tab>('lookup')
  const [meta, setMeta] = useState<Meta | null>(null)
  const [asOf, setAsOf] = useState('2026-10-01')
  const [selected, setSelected] = useState<string | null>(null)
  const s = t(lang)

  useEffect(() => {
    api<Meta>('/meta')
      .then((m) => {
        setMeta(m)
        setAsOf(m.default_as_of)
      })
      .catch(() => setMeta(null))
  }, [])

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
            <StrataMark />
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
              <label className="hidden items-center gap-2 text-[13px] text-muted sm:flex">
                {s.asOf}
                <input
                  type="date"
                  value={asOf}
                  onChange={(e) => e.target.value && setAsOf(e.target.value)}
                  className="rounded-lg border border-hairline bg-white/80 px-2 py-1 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                />
              </label>
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

      <main className="mx-auto min-h-[72vh] max-w-[1200px] px-5 py-10">
        {tab === 'lookup' && <LookupView s={s} lang={lang} asOf={asOf} selectedId={selected} onSelect={setSelected} />}
        {tab === 'time' && <TimeMachine s={s} categories={meta?.categories ?? {}} onOpenAddress={openAddress} />}
        {tab === 'changes' && <ChangesView s={s} onOpenAddress={openAddress} />}
        {tab === 'rules' && <RulesView s={s} categories={meta?.categories ?? {}} />}
        {tab === 'audit' && <AuditView s={s} />}
      </main>

      <footer className="border-t border-black/[0.06] bg-[#fbfbfd]">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-5 py-6 text-[12px] text-faint">
          <span className="flex items-center gap-2">
            <StrataMark size={14} /> Strata · Hack-Nation 7 · Challenge 2
          </span>
          <span>
            {meta ? `${meta.n_rules} rules · ${meta.n_addresses} properties · ` : ''}Public data only · Census Geocoder · RealPage starter corpus
          </span>
        </div>
      </footer>
    </div>
  )
}
