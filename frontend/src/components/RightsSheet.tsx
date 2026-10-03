import { useEffect } from 'react'
import { catLabel, type Lang, type Strings } from '../lib/i18n'
import type { LookupAnswer, ResultItem } from '../lib/types'
import { StrataMark } from './ui'

const COPY = {
  en: {
    title: 'Your housing rules at a glance',
    lead: 'The rules that govern this building today, in plain language, with where each one comes from.',
    unsure: 'Not certain for this building',
    unsureWhy: 'Coverage depends on a fact public records don’t show. Ask your landlord or a local tenant organization.',
    upcoming: 'Coming up',
    print: 'Print or save as PDF',
  },
  es: {
    title: 'Sus reglas de vivienda de un vistazo',
    lead: 'Las reglas que rigen este edificio hoy, en lenguaje sencillo, con el origen de cada una.',
    unsure: 'No es seguro para este edificio',
    unsureWhy: 'Depende de un dato que los registros públicos no muestran. Pregunte a su arrendador o a una organización local de inquilinos.',
    upcoming: 'Próximamente',
    print: 'Imprimir o guardar como PDF',
  },
}

export default function RightsSheet({
  answer,
  s,
  lang,
  onClose,
}: {
  answer: LookupAnswer
  s: Strings
  lang: Lang
  onClose: () => void
}) {
  const c = COPY[lang]
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const byCat = new Map<string, ResultItem[]>()
  for (const r of answer.results) byCat.set(r.category_label, [...(byCat.get(r.category_label) ?? []), r])
  const sections = [...byCat.entries()].map(([label, items]) => {
    const governing = items.filter((r) => r.result === 'applies')
    const unsure = items.filter((r) => r.result === 'unknown')
    const upcoming = items.filter((r) => r.result === 'not_yet_effective')
    return { label, governing, unsure, upcoming }
  })
  const text = (r: ResultItem) => (lang === 'es' && r.requirement_es ? r.requirement_es : r.requirement)

  return (
    <div className="backdrop-in rights-overlay fixed inset-0 z-[1000] flex items-start justify-center overflow-y-auto bg-black/30 p-4 backdrop-blur-sm sm:p-8" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="sheet-up rights-sheet w-full max-w-2xl rounded-[28px] bg-white p-8 shadow-2xl sm:p-10">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2 text-[15px] font-semibold">
            <StrataMark size={18} /> Strata
          </div>
          <div className="no-print flex gap-2">
            <button onClick={() => window.print()} className="btn-primary px-4 py-2 text-[13px]">
              {c.print}
            </button>
            <button onClick={onClose} aria-label="Close" className="grid h-9 w-9 place-items-center rounded-full bg-fill text-muted hover:text-ink">
              ✕
            </button>
          </div>
        </div>
        <h2 className="mt-6 text-[30px] font-semibold leading-tight tracking-[-0.02em]">{c.title}</h2>
        <p className="mt-1 text-[17px] font-medium">{answer.address.street_address}</p>
        <p className="text-[14px] text-muted">
          {answer.jurisdiction_stack.slice().reverse().join(' · ')} · {s.asOf} {answer.as_of}
        </p>
        <p className="mt-4 text-[15px] leading-relaxed text-ink-2">{c.lead}</p>

        <div className="mt-6 divide-y divide-hairline/70 border-y border-hairline/70">
          {sections.map(({ label, governing, unsure, upcoming }) => (
            <section key={label} className="break-inside-avoid py-5">
              <h3 className="text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">{catLabel(label, lang)}</h3>
              {governing.map((r) => (
                <div key={r.team_rule_id} className="mt-2">
                  {(lang === 'es' ? r.key_value_es || r.key_value : r.key_value) && (
                    <p className="text-[19px] font-semibold tracking-tight">{lang === 'es' ? r.key_value_es || r.key_value : r.key_value}</p>
                  )}
                  <p className="text-[15px] leading-relaxed text-ink-2">{text(r)}</p>
                  <p className="mt-1 text-[12px] text-faint">
                    {r.citation} · {r.jurisdiction}
                  </p>
                </div>
              ))}
              {governing.length === 0 && unsure.length > 0 && (
                <div className="mt-2">
                  <p className="text-[15px] font-semibold text-unknown">{c.unsure}</p>
                  <p className="text-[14px] leading-relaxed text-ink-2">{text(unsure[0])}</p>
                  <p className="mt-1 text-[12px] text-faint">
                    {c.unsureWhy} · {unsure.map((r) => r.citation).join(' · ')}
                  </p>
                </div>
              )}
              {upcoming.map((r) => (
                <p key={r.team_rule_id} className="mt-2 text-[13px] text-future">
                  <span className="font-semibold">
                    {c.upcoming} ({r.effective_date}):
                  </span>{' '}
                  {text(r)}
                </p>
              ))}
            </section>
          ))}
        </div>
        <p className="mt-6 text-[12px] leading-relaxed text-faint">{answer.disclaimer}</p>
      </div>
    </div>
  )
}
