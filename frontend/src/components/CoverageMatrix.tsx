import type { Rule } from '../lib/types'
import { Card } from './ui'

const ORDER = ['CA', 'NJ', 'MA']

interface Props {
  grid: Record<string, string>
  rules: Rule[]
  categories: Record<string, string>
  onPick: (jurisdiction: string, category: string) => void
}

function cellStyle(rules: Rule[], status: string | undefined) {
  if (rules.some((r) => r.status === 'in_force')) return { cls: 'bg-applies-bg text-applies', label: String(rules.filter((r) => r.status === 'in_force').length) }
  if (rules.some((r) => r.status === 'not_yet_effective')) return { cls: 'bg-future-bg text-future', label: 'Soon' }
  if (rules.some((r) => r.status === 'pending')) return { cls: 'bg-pending-bg text-pending', label: 'Bill' }
  if (rules.some((r) => r.status === 'failed')) return { cls: 'bg-superseded-bg text-superseded', label: 'Failed' }
  if (status === 'no_rule_stated') return { cls: 'bg-fill text-ink-2', label: 'None' }
  return { cls: 'bg-white text-faint', label: '—' }
}

export default function CoverageMatrix({ grid, rules, categories, onPick }: Props) {
  const jurs = [...new Set(Object.keys(grid).map((k) => k.split('|')[0]))].sort((a, b) => {
    const sa = a.includes(',') ? a.split(', ')[1] : a
    const sb = b.includes(',') ? b.split(', ')[1] : b
    return ORDER.indexOf(sa) - ORDER.indexOf(sb) || Number(a.includes(',')) - Number(b.includes(',')) || a.localeCompare(b)
  })
  const cats = Object.keys(categories)
  return (
    <Card className="overflow-hidden">
      <div className="px-7 pb-4 pt-6">
        <h3 className="text-[21px] font-semibold tracking-tight">Coverage at a glance</h3>
        <p className="text-[14px] text-muted">
          Every jurisdiction × category the system was asked about. Numbers are rules in force; “None” means the law says there is no rule at that level; “—” means
          the corpus is silent (the state layer governs).
        </p>
      </div>
      <div className="overflow-x-auto border-t border-hairline/60">
        <table className="min-w-full text-[13px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-5 py-3 font-semibold">Jurisdiction</th>
              {cats.map((c) => (
                <th key={c} className="px-2 py-3 text-center font-semibold">
                  {categories[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline/50">
            {jurs.map((j) => (
              <tr key={j}>
                <td className="whitespace-nowrap px-5 py-2 font-medium">
                  <span className={`mr-2 inline-block h-2 w-2 rounded-[3px] ${j.includes(',') ? 'bg-layer-city' : 'bg-layer-state'}`} />
                  {j}
                  {j === 'Oakland, CA' && <span className="ml-2 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-semibold text-accent">NEW</span>}
                </td>
                {cats.map((c) => {
                  const cellRules = rules.filter((r) => r.jurisdiction === j && r.category === c)
                  const st = cellStyle(cellRules, grid[`${j}|${c}`])
                  return (
                    <td key={c} className="px-2 py-1.5 text-center">
                      <button
                        onClick={() => onPick(j, c)}
                        title={cellRules.map((r) => `${r.citation} (${r.status})`).join('\n') || grid[`${j}|${c}`]}
                        className={`w-full rounded-lg px-2 py-1.5 font-semibold transition hover:ring-2 hover:ring-accent/30 ${st.cls}`}
                      >
                        {st.label}
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
