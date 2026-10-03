import { divIcon, type LatLngBoundsExpression } from 'leaflet'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { api } from '../lib/api'
import type { Strings } from '../lib/i18n'
import { Card, RESULT_COLOR, Segmented, type Shade } from './ui'

interface Point {
  id: string
  lat: number
  lon: number
  street: string
  city: string | null
  r: Record<string, Shade>
}
interface MapData {
  as_of: string
  points: Point[]
  counts: Record<string, Record<string, number>>
  not_mapped: number
}
interface TimelineEvent {
  date: string
  rule_id: string
  jurisdiction: string
  category: string
  category_label: string
  title: string
  citation: string
  conflict: boolean
}
interface Timeline {
  events: TimelineEvent[]
  not_law: { rule_id: string; jurisdiction: string; title: string; citation: string; status: string; category_label: string }[]
}

export type Region = 'BAY' | 'LA' | 'SD' | 'NJ' | 'BOS'
export interface TimeState {
  date: string
  lens: string
  region: Region
}

// Metro views: every building is visible on its own, so changes are easy to see.
const REGIONS: Record<Region, LatLngBoundsExpression> = {
  BAY: [
    [37.7, -122.52],
    [37.9, -122.15],
  ],
  LA: [
    [33.95, -118.52],
    [34.28, -118.2],
  ],
  SD: [
    [32.66, -117.27],
    [32.83, -117.03],
  ],
  NJ: [
    [40.69, -74.26],
    [40.77, -74.01],
  ],
  BOS: [
    [42.27, -71.17],
    [42.41, -71.0],
  ],
}
const REGION_OPTIONS: [Region, string][] = [
  ['BAY', 'Bay Area'],
  ['LA', 'Los Angeles'],
  ['SD', 'San Diego'],
  ['NJ', 'New Jersey'],
  ['BOS', 'Boston'],
]
const REGION_OF: Record<string, Region> = {
  CA: 'BAY', 'San Francisco, CA': 'BAY', 'Berkeley, CA': 'BAY', 'Oakland, CA': 'BAY',
  'Los Angeles, CA': 'LA', 'Santa Ana, CA': 'LA', 'San Diego, CA': 'SD',
  NJ: 'NJ', 'Jersey City, NJ': 'NJ', 'Hoboken, NJ': 'NJ', 'Newark, NJ': 'NJ',
  MA: 'BOS', 'Boston, MA': 'BOS', 'Cambridge, MA': 'BOS',
}
const START = Date.UTC(2024, 0, 1)
const END = Date.UTC(2028, 11, 31)
const DAY = 86_400_000
const TOTAL = Math.round((END - START) / DAY)
const toISO = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const toMs = (iso: string) => Date.parse(`${iso}T00:00:00Z`)
const dayOf = (iso: string) => Math.round((toMs(iso) - START) / DAY)
const ORDER: Shade[] = ['applies', 'unknown', 'not_yet_effective', 'pending', 'superseded', 'none']
// Playback: ~11 s for five years, slowing near each change and pausing on it.
const BASE_SPEED = 165 // days per second
const DWELL_MS = 2200

function FitRegion({ region }: { region: Region }) {
  const map = useMap()
  useEffect(() => {
    // Leave room for the date/legend panel on the left.
    map.flyToBounds(REGIONS[region], { duration: 0.9, paddingTopLeft: [300, 40], paddingBottomRight: [30, 30] })
  }, [map, region])
  return null
}

function Tween({ value }: { value: number }) {
  const [shown, setShown] = useState(value)
  const from = useRef(value)
  useEffect(() => {
    const start = performance.now()
    const a = from.current
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 600)
      const v = Math.round(a + (value - a) * (1 - Math.pow(1 - k, 3)))
      setShown(v)
      if (k < 1) raf = requestAnimationFrame(tick)
      else from.current = value
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <span className="tabular-nums">{shown}</span>
}

interface Toast {
  key: number
  date: string
  events: TimelineEvent[]
  delta: [Shade, number][]
}

export default function TimeMachine({
  s,
  categories,
  onOpenAddress,
  initial,
  onChange,
}: {
  s: Strings
  categories: Record<string, string>
  onOpenAddress: (id: string) => void
  initial?: Partial<TimeState>
  onChange?: (st: TimeState) => void
}) {
  const startDate = initial?.date && /^\d{4}-\d{2}-\d{2}$/.test(initial.date) ? initial.date : '2025-10-01'
  const [dayF, setDayF] = useState(Math.min(TOTAL, Math.max(0, dayOf(startDate))))
  const [lens, setLens] = useState(initial?.lens || 'algorithmic_rent_setting')
  const [region, setRegion] = useState<Region>(initial?.region && initial.region in REGIONS ? initial.region : 'BAY')
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [snapshots, setSnapshots] = useState<Map<string, MapData>>(new Map())
  const [playing, setPlaying] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const [changed, setChanged] = useState<{ ids: Set<string>; stamp: number }>({ ids: new Set(), stamp: 0 })
  const dayRef = useRef(dayF)
  const dwellUntil = useRef(0)
  const prevKey = useRef<string | null>(null)
  const prevShades = useRef<Map<string, Shade>>(new Map())
  const toastTimer = useRef<number | undefined>(undefined)

  const day = Math.floor(dayF)
  const iso = toISO(START + day * DAY)

  // Laws only change on effective dates, so one snapshot per date covers the whole timeline.
  const keyDates = useMemo(() => {
    const d = new Set<string>(['2024-01-01'])
    timeline?.events.forEach((e) => d.add(e.date))
    return [...d].sort()
  }, [timeline])
  const snapKey = useMemo(() => [...keyDates].reverse().find((k) => k <= iso) ?? keyDates[0], [keyDates, iso])
  const data = snapshots.get(snapKey) ?? null

  useEffect(() => {
    api<Timeline>('/timeline').then(setTimeline)
  }, [])

  useEffect(() => {
    if (!timeline) return
    let alive = true
    Promise.all(keyDates.map((k) => api<MapData>(`/map?as_of=${k}`).then((m) => [k, m] as const))).then((pairs) => {
      if (alive) setSnapshots(new Map(pairs))
    })
    return () => {
      alive = false
    }
  }, [timeline, keyDates])

  useEffect(() => {
    onChange?.({ date: iso, lens, region })
  }, [iso, lens, region, onChange])

  // Detect what changed when the timeline crosses an effective date.
  useEffect(() => {
    if (!data) return
    const shades = new Map(data.points.map((p) => [p.id, p.r[lens] ?? 'none'] as [string, Shade]))
    if (prevKey.current && prevKey.current !== snapKey) {
      const ids = new Set<string>()
      const delta = new Map<Shade, number>()
      shades.forEach((sh, id) => {
        const before = prevShades.current.get(id)
        if (before && before !== sh) {
          ids.add(id)
          delta.set(sh, (delta.get(sh) ?? 0) + 1)
        }
      })
      setChanged((c) => ({ ids, stamp: c.stamp + 1 }))
      const forward = snapKey > prevKey.current
      const evs = (timeline?.events ?? []).filter((e) => e.date === snapKey)
      if (forward && evs.length) {
        window.clearTimeout(toastTimer.current)
        setToast({ key: Date.now(), date: snapKey, events: evs, delta: [...delta.entries()] })
        toastTimer.current = window.setTimeout(() => setToast(null), 5000)
      }
    }
    prevKey.current = snapKey
    prevShades.current = shades
  }, [data, snapKey, lens, timeline])

  // Smooth playback: continuous date, eased near changes, a short pause on each one.
  useEffect(() => {
    if (!playing) return
    let raf = 0
    let last = performance.now()
    const events = keyDates.map(dayOf).filter((d) => d > 0)
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      if (now < dwellUntil.current) {
        raf = requestAnimationFrame(tick)
        return
      }
      const cur = dayRef.current
      const next = events.find((d) => d > cur)
      const dist = next === undefined ? Infinity : next - cur
      const ease = dist < 60 ? 0.25 + 0.75 * (dist / 60) : 1
      let nxt = cur + BASE_SPEED * ease * dt
      if (next !== undefined && nxt >= next) {
        nxt = next
        dwellUntil.current = now + DWELL_MS
      }
      if (nxt >= TOTAL) {
        nxt = TOTAL
        setPlaying(false)
      }
      dayRef.current = nxt
      setDayF(nxt)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, keyDates])

  const seek = useCallback((d: number) => {
    setPlaying(false)
    dayRef.current = d
    setDayF(d)
  }, [])

  const jump = useCallback(
    (e: TimelineEvent) => {
      seek(dayOf(e.date))
      setLens(e.category)
      const r = REGION_OF[e.jurisdiction]
      if (r) setRegion(r)
    },
    [seek],
  )

  const markers = useMemo(
    () =>
      data?.points.map((p) => {
        const shade = p.r[lens] ?? 'none'
        const color = RESULT_COLOR[shade]
        const isNew = changed.ids.has(p.id)
        const icon = divIcon({
          className: 'tm-icon',
          iconSize: [14, 14],
          html: `<span class="tm-wrap ${isNew ? 'tm-changed' : ''}" style="--ring:${color}"><span class="tm-pt" style="background:${color}"></span></span>`,
        })
        return (
          <Marker key={`${p.id}-${isNew ? changed.stamp : 0}`} position={[p.lat, p.lon]} icon={icon}>
            <Popup>
              <p className="text-[14px] font-semibold">{p.street}</p>
              <p className="text-[12px] text-muted">
                {p.city} · {p.id}
              </p>
              <p className="mt-1 text-[12px]">
                {categories[lens]}: <b>{shade === 'none' ? s.none : s.results[shade]}</b>
              </p>
              <button onClick={() => onOpenAddress(p.id)} className="mt-1 text-[12px] font-medium text-accent">
                {s.openLookup} →
              </button>
            </Popup>
          </Marker>
        )
      }) ?? [],
    [data, lens, changed, categories, onOpenAddress, s],
  )

  const counts = data?.counts[lens] ?? {}
  const pretty = new Date(START + day * DAY).toLocaleDateString(s.asOf === 'As of' ? 'en-US' : 'es-MX', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
  const nextEvent = timeline?.events.find((e) => e.date > iso)
  const ready = snapshots.size > 0 && snapshots.size === keyDates.length

  return (
    <div className="space-y-10">
      <section className="mx-auto max-w-3xl pt-6 text-center">
        <p className="page-in eyebrow text-accent">{s.tabTime}</p>
        <h1 className="page-in mt-3 text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[56px]" style={{ animationDelay: '80ms' }}>
          {s.landing.timeTitle}
        </h1>
        <p className="page-in mx-auto mt-4 max-w-xl text-[19px] leading-snug text-muted" style={{ animationDelay: '160ms' }}>
          {s.landing.timeBody}
        </p>
      </section>

      <div className="page-in grid gap-6 xl:grid-cols-[1fr_340px]" style={{ animationDelay: '240ms' }}>
        <Card className="overflow-hidden">
          <div className="relative h-[580px]">
            <MapContainer bounds={REGIONS[region]} zoomControl={false} scrollWheelZoom className="h-full w-full">
              <TileLayer
                attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                maxZoom={16}
              />
              <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}" maxZoom={16} />
              <FitRegion region={region} />
              {markers}
            </MapContainer>

            {!ready && (
              <div className="absolute inset-0 z-[600] grid place-items-center bg-white/60 backdrop-blur-sm">
                <span className="flex items-center gap-3 text-[14px] text-muted">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-hairline border-t-accent" />
                  {s.loading}
                </span>
              </div>
            )}

            <div className="glass absolute left-4 top-4 z-[500] w-[270px] rounded-2xl p-5 shadow-[0_8px_30px_rgba(0,0,0,0.10)]">
              <p className="eyebrow">{s.asOf}</p>
              <p key={snapKey} className="page-in text-[26px] font-semibold capitalize leading-tight tracking-tight">
                {pretty}
              </p>
              <select
                value={lens}
                onChange={(e) => setLens(e.target.value)}
                className="mt-3 w-full rounded-lg border border-hairline bg-white/80 px-2.5 py-1.5 text-[13px] font-medium focus:outline-none"
              >
                {Object.entries(categories).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
              <ul className="mt-3 space-y-1.5">
                {ORDER.filter((k) => counts[k]).map((k) => (
                  <li key={k} className="flex items-center justify-between text-[13px]">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full transition-colors duration-500" style={{ background: RESULT_COLOR[k] }} />
                      {k === 'none' ? s.none : s.results[k as Exclude<Shade, 'none'>]}
                    </span>
                    <span className="text-muted">
                      <Tween value={counts[k] ?? 0} />
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="absolute right-4 top-4 z-[500]">
              <div className="glass rounded-full p-0.5 shadow-[0_4px_16px_rgba(0,0,0,0.08)]">
                <Segmented size="sm" value={region} onChange={setRegion} options={REGION_OPTIONS} />
              </div>
            </div>

            {toast && (
              <div key={toast.key} className="toast-in glass absolute bottom-5 left-1/2 z-[550] w-[min(92%,460px)] rounded-2xl p-5 shadow-[0_16px_40px_rgba(0,0,0,0.18)]">
                <p className="eyebrow text-accent">{toast.date}</p>
                {toast.events.slice(0, 2).map((e) => (
                  <p key={e.rule_id} className="mt-1 text-[15px] font-semibold leading-snug">
                    {e.jurisdiction} · {e.title}
                  </p>
                ))}
                {toast.events.length > 2 && <p className="text-[12px] text-muted">+{toast.events.length - 2} more</p>}
                {toast.delta.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {toast.delta.map(([sh, n]) => (
                      <span key={sh} className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-[12px] font-semibold shadow-sm">
                        <span className="h-2 w-2 rounded-full" style={{ background: RESULT_COLOR[sh] }} />
                        {n} {s.buildings} → {sh === 'none' ? s.none : s.results[sh as Exclude<Shade, 'none'>]}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="border-t border-hairline/60 px-6 pb-6 pt-5">
            <div className="flex items-center gap-5">
              <button
                onClick={() => {
                  if (dayRef.current >= TOTAL - 1) seek(0)
                  dwellUntil.current = 0
                  setPlaying(!playing)
                }}
                disabled={!ready}
                aria-label={playing ? s.pause : s.play}
                className={`grid h-12 w-12 shrink-0 place-items-center rounded-full bg-ink text-white transition hover:bg-black active:scale-95 disabled:opacity-40 ${playing ? 'playhead-glow' : ''}`}
              >
                {playing ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                    <rect x="2" y="1" width="3.5" height="12" rx="1" />
                    <rect x="8.5" y="1" width="3.5" height="12" rx="1" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                    <path d="M3 1.5v11a.5.5 0 0 0 .77.42l8.5-5.5a.5.5 0 0 0 0-.84l-8.5-5.5A.5.5 0 0 0 3 1.5Z" />
                  </svg>
                )}
              </button>
              <div className="relative flex-1 pt-4">
                {/* progress fill + event markers */}
                <div className="pointer-events-none absolute inset-x-[11px] top-[23px] h-1 rounded-full bg-hairline">
                  <div className="h-full rounded-full bg-gradient-to-r from-[#5856d6] to-accent" style={{ width: `${(dayF / TOTAL) * 100}%` }} />
                </div>
                <div className="pointer-events-none absolute inset-x-[11px] top-[17px] h-4">
                  {timeline?.events.map((e) => {
                    const passed = e.date <= iso
                    const active = e.date === snapKey
                    return (
                      <span
                        key={e.rule_id}
                        className="absolute top-0 h-4 w-4 -translate-x-1/2 rounded-full border-2 border-white shadow transition-all duration-500"
                        style={{
                          left: `${(dayOf(e.date) / TOTAL) * 100}%`,
                          background: passed ? (e.conflict ? '#ff9f0a' : '#0071e3') : '#d2d2d7',
                          transform: `translateX(-50%) scale(${active ? 1.35 : 0.8})`,
                        }}
                      />
                    )
                  })}
                </div>
                <input
                  type="range"
                  className="timeline relative w-full bg-transparent"
                  style={{ background: 'transparent' }}
                  min={0}
                  max={TOTAL}
                  step={1}
                  value={day}
                  onChange={(e) => seek(Number(e.target.value))}
                />
                <div className="mt-2 flex justify-between text-[11px] tabular-nums text-faint">
                  {[2024, 2025, 2026, 2027, 2028].map((y) => (
                    <span key={y}>{y}</span>
                  ))}
                </div>
              </div>
            </div>
            {nextEvent && (
              <p className="mt-4 text-[13px] text-muted">
                Next change ·{' '}
                <button onClick={() => jump(nextEvent)} className="font-medium text-accent hover:underline">
                  {nextEvent.date} — {nextEvent.jurisdiction}: {nextEvent.title}
                </button>
              </p>
            )}
            {data && data.not_mapped > 0 && (
              <p className="mt-1 text-[11px] text-faint">
                {data.not_mapped} {s.notMapped}
              </p>
            )}
          </div>
        </Card>

        <Card className="flex max-h-[720px] flex-col overflow-hidden">
          <div className="px-6 pb-3 pt-6">
            <h3 className="text-[19px] font-semibold tracking-tight">{s.whatChanged}</h3>
          </div>
          <ol className="flex-1 overflow-y-auto px-3 pb-3">
            {timeline?.events.map((e, i) => {
              const past = e.date <= iso
              const active = e.date === snapKey
              return (
                <li key={e.rule_id} className="stagger" style={{ animationDelay: `${300 + i * 40}ms` }}>
                  <button
                    onClick={() => jump(e)}
                    className={`group flex w-full gap-3 rounded-xl px-3 py-2.5 text-left transition hover:bg-fill ${active ? 'bg-accent/[0.07] ring-1 ring-accent/30' : ''}`}
                  >
                    <span
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full transition-colors duration-500"
                      style={{ background: past ? (e.conflict ? '#ff9f0a' : '#0071e3') : '#d2d2d7' }}
                    />
                    <span className={`transition-opacity duration-500 ${past ? '' : 'opacity-55'}`}>
                      <span className="block text-[12px] tabular-nums text-faint">
                        {e.date} · {e.jurisdiction}
                      </span>
                      <span className="block text-[14px] font-medium leading-snug">{e.title}</span>
                      <span className="block text-[12px] text-muted">{e.category_label}</span>
                    </span>
                  </button>
                </li>
              )
            })}
            {timeline && timeline.not_law.length > 0 && (
              <>
                <li className="eyebrow px-3 pb-1 pt-4">{s.notLaw}</li>
                {timeline.not_law.map((n) => (
                  <li key={n.rule_id} className="flex gap-3 px-3 py-2">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: n.status === 'pending' ? '#bf5af2' : '#a1a1a6' }} />
                    <span>
                      <span className="block text-[12px] text-faint">
                        {n.status} · {n.jurisdiction}
                      </span>
                      <span className="block text-[14px] leading-snug">{n.title}</span>
                    </span>
                  </li>
                ))}
              </>
            )}
          </ol>
        </Card>
      </div>
    </div>
  )
}
