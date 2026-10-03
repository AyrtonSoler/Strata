import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Strings } from '../lib/i18n'

/** Adds "in" once the element scrolls into view (CSS handles the motion). */
function useInView<T extends HTMLElement>(threshold = 0.25) {
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true)
          io.disconnect()
        }
      },
      { threshold },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [threshold])
  return [ref, inView] as const
}

export function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.2)
  return (
    <div ref={ref} className={`reveal ${inView ? 'in' : ''} ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

function CountUp({ value }: { value: string }) {
  const [ref, inView] = useInView<HTMLSpanElement>(0.5)
  const target = parseInt(value, 10)
  const suffix = value.replace(/^\d+/, '')
  const [n, setN] = useState(0)
  useEffect(() => {
    if (!inView || Number.isNaN(target)) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      setN(target)
      return
    }
    const start = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 1400)
      setN(Math.round(target * (1 - Math.pow(1 - k, 3))))
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, target])
  return (
    <span ref={ref} className="tabular-nums">
      {Number.isNaN(target) ? value : `${n}${suffix}`}
    </span>
  )
}

/** The Strata mark as a scene: three layers of law settling on a building. */
export function StrataVisual() {
  const layers = [
    { label: 'State', color: '#5856d6', w: 300, delay: 300 },
    { label: 'County', color: '#8e8e93', w: 252, delay: 550 },
    { label: 'City', color: '#0a9e8f', w: 204, delay: 800 },
  ]
  return (
    <div className="anim-float relative mx-auto flex w-[320px] flex-col items-center" aria-hidden="true">
      <div className="flex w-full flex-col items-center gap-2.5">
        {layers.map((l) => (
          <div
            key={l.label}
            className="anim-layer flex h-10 items-center justify-between rounded-2xl px-4 text-[13px] font-semibold text-white shadow-[0_10px_30px_rgba(0,0,0,0.12)]"
            style={{ width: l.w, background: l.color, animationDelay: `${l.delay}ms` }}
          >
            <span>{l.label}</span>
            <span className="h-1.5 w-10 rounded-full bg-white/40" />
          </div>
        ))}
      </div>
      <svg className="anim-fade-up mt-3" style={{ animationDelay: '1100ms' }} width="180" height="120" viewBox="0 0 180 120">
        <rect x="30" y="10" width="120" height="110" rx="10" fill="#1d1d1f" />
        {[0, 1, 2, 3].map((r) =>
          [0, 1, 2, 3].map((c) => (
            <rect key={`${r}-${c}`} x={44 + c * 25} y={24 + r * 22} width="15" height="12" rx="3" fill={(r + c) % 3 === 0 ? '#ffd60a' : '#3a3a3c'} />
          )),
        )}
      </svg>
    </div>
  )
}

function Section({ eyebrow, title, children, dark = false }: { eyebrow: string; title: string; children: ReactNode; dark?: boolean }) {
  return (
    <section className={`py-28 sm:py-36 ${dark ? 'bleed bg-[#0b0b0f] text-white' : ''}`}>
      <div className="mx-auto max-w-5xl px-5">
        <Reveal>
          <p className={`eyebrow ${dark ? 'text-[#2997ff]' : 'text-accent'}`}>{eyebrow}</p>
          <h2 className="mt-3 max-w-3xl text-[40px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[56px]">{title}</h2>
        </Reveal>
        <div className="mt-14">{children}</div>
      </div>
    </section>
  )
}

export default function Landing({ s, onExample, onTimeMachine, onSearch }: { s: Strings; onExample: (id: string) => void; onTimeMachine: () => void; onSearch: () => void }) {
  const L = s.landing
  return (
    <div>
      <Section eyebrow={L.problemEyebrow} title={L.problemTitle}>
        <div className="grid items-center gap-14 md:grid-cols-2">
          <Reveal delay={100}>
            <p className="text-[21px] leading-relaxed text-muted">{L.problemBody}</p>
          </Reveal>
          <div className="space-y-3">
            {L.layers.map(([name, body], i) => (
              <Reveal key={name} delay={200 + i * 150}>
                <div
                  className="flex items-center justify-between rounded-2xl px-6 py-5 text-white shadow-[0_12px_30px_rgba(0,0,0,0.10)]"
                  style={{ background: ['#0a9e8f', '#8e8e93', '#5856d6'][i], marginLeft: i * 24 }}
                >
                  <span className="text-[19px] font-semibold">{name}</span>
                  <span className="max-w-[60%] text-right text-[13px] opacity-90">{body}</span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Section>

      <Section eyebrow={L.howEyebrow} title={L.howTitle}>
        <div className="grid gap-5 md:grid-cols-3">
          {s.how.map(([title, body], i) => (
            <Reveal key={title} delay={i * 150}>
              <div className="card h-full p-8">
                <p className="text-[40px] font-semibold leading-none tracking-tight text-accent/25">0{i + 1}</p>
                <p className="mt-6 text-[21px] font-semibold tracking-tight">{title}</p>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section eyebrow={L.timeEyebrow} title={L.timeTitle} dark>
        <div className="grid items-center gap-14 md:grid-cols-2">
          <Reveal delay={100}>
            <p className="text-[21px] leading-relaxed text-white/70">{L.timeBody}</p>
            <button onClick={onTimeMachine} className="btn-primary mt-8">
              {L.timeCta} →
            </button>
          </Reveal>
          <Reveal delay={250}>
            <div className="rounded-[28px] bg-white/[0.04] p-8 ring-1 ring-white/10">
              <div className="grid grid-cols-10 gap-2.5">
                {Array.from({ length: 60 }).map((_, i) => (
                  <span key={i} className="tm-dot aspect-square rounded-full" style={{ animationDelay: `${600 + ((i * 37) % 60) * 28}ms` }} />
                ))}
              </div>
              <div className="mt-6 flex items-center justify-between text-[13px] text-white/60">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#0a84ff]" /> {L.timeFrom}
                </span>
                <span className="h-px flex-1 bg-white/15 mx-4" />
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#30d158]" /> {L.timeTo}
                </span>
              </div>
            </div>
          </Reveal>
        </div>
      </Section>

      <Section eyebrow={L.evidenceEyebrow} title={L.evidenceTitle}>
        <div className="grid items-center gap-14 md:grid-cols-2">
          <Reveal delay={100}>
            <p className="text-[21px] leading-relaxed text-muted">{L.evidenceBody}</p>
            <button onClick={() => onExample('A0016')} className="btn-primary mt-8">
              {L.evidenceCta} →
            </button>
          </Reveal>
          <Reveal delay={250}>
            <figure className="card p-8">
              <blockquote className="text-[19px] leading-[1.7] text-ink-2">
                “…an owner of residential real property shall not, over the course of any 12-month period, increase the gross rental rate for a dwelling or a unit{' '}
                <span className="sweep rounded px-0.5 text-ink">more than 5 percent plus the percentage change in the cost of living, or 10 percent, whichever is lower</span>…”
              </blockquote>
              <figcaption className="mt-5 text-[13px] text-faint">{L.evidenceCite}</figcaption>
            </figure>
          </Reveal>
        </div>
      </Section>

      <Section eyebrow={L.forEyebrow} title={L.forTitle}>
        <div className="grid gap-5 md:grid-cols-3">
          {L.personas.map(([who, body], i) => (
            <Reveal key={who} delay={i * 150}>
              <div className="h-full rounded-[22px] border border-hairline/70 bg-white/60 p-8">
                <p className="text-[21px] font-semibold tracking-tight">{who}</p>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      <section className="bleed border-y border-hairline/60 bg-white py-24">
        <div className="mx-auto max-w-5xl px-5">
          <Reveal>
            <p className="text-center text-[28px] font-semibold tracking-tight">{L.statsTitle}</p>
          </Reveal>
          <div className="mt-12 grid grid-cols-2 gap-10 md:grid-cols-4">
            {s.stats.map(([n, label], i) => (
              <Reveal key={label} delay={i * 120} className="text-center">
                <p className="text-[56px] font-semibold leading-none tracking-[-0.04em]">
                  <CountUp value={n} />
                </p>
                <p className="mt-2 text-[14px] text-muted">{label}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="py-32 text-center">
        <Reveal>
          <h2 className="text-[44px] font-semibold tracking-[-0.03em] sm:text-[64px]">{L.ctaTitle}</h2>
          <button onClick={onSearch} className="btn-primary mt-8 px-7 py-3 text-[17px]">
            {L.ctaButton}
          </button>
        </Reveal>
      </section>
    </div>
  )
}
