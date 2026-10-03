import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'
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

type Region = 'CA' | 'NJ' | 'MA'
const REGIONS: Record<Region, LatLngBoundsExpression> = {
  CA: [
    [32.68, -122.55],
    [37.95, -117.0],
  ],
  NJ: [
    [40.69, -74.26],
    [40.77, -74.01],
  ],
  MA: [
    [42.27, -71.17],
    [42.41, -71.0],
  ],
}
const START = Date.UTC(2024, 0, 1)
const END = Date.UTC(2028, 11, 31)
const DAY = 86_400_000
const toISO = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const toMs = (iso: string) => Date.parse(`${iso}T00:00:00Z`)
const ORDER: Shade[] = ['applies', 'unknown', 'not_yet_effective', 'pending', 'superseded', 'none']

function FitRegion({ region }: { region: Region }) {
  const map = useMap()
  useEffect(() => {
    map.flyToBounds(REGIONS[region], { duration: 0.8, padding: [24, 24] })
  }, [map, region])
  return null
}

export default function TimeMachine({
  s,
  categories,
  onOpenAddress,
}: {
  s: Strings
  categories: Record<string, string>
  onOpenAddress: (id: string) => void
}) {
  const [day, setDay] = useState(Math.round((toMs('2025-10-01') - START) / DAY))
  const [lens, setLens] = useState('algorithmic_rent_setting')
  const [region, setRegion] = useState<Region>('CA')
  const [data, setData] = useState<MapData | null>(null)
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [playing, setPlaying] = useState(false)
  const cache = useRef(new Map<string, MapData>())
  const iso = toISO(START + day * DAY)

  useEffect(() => {
    api<Timeline>('/timeline').then(setTimeline)
  }, [])

  useEffect(() => {
    const hit = cache.current.get(iso)
    if (hit) {
      setData(hit)
      return
    }
    const id = setTimeout(() => {
      api<MapData>(`/map?as_of=${iso}`).then((d) => {
        cache.current.set(iso, d)
        setData(d)
      })
    }, 60)
    return () => clearTimeout(id)
  }, [iso])

  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => {
      setDay((d) => {
        const next = d + 30
        if (START + next * DAY > END) {
          setPlaying(false)
          return d
        }
        return next
      })
    }, 450)
    return () => clearInterval(id)
  }, [playing])

  const jump = useCallback((e: TimelineEvent) => {
    setPlaying(false)
    setDay(Math.round((toMs(e.date) - START) / DAY))
    setLens(e.category)
    const st = e.jurisdiction.includes(',') ? e.jurisdiction.split(', ')[1] : e.jurisdiction
    if (st === 'CA' || st === 'NJ' || st === 'MA') setRegion(st)
  }, [])

  const totalDays = Math.round((END - START) / DAY)
  const counts = data?.counts[lens] ?? {}
  const prettyDate = new Date(START + day * DAY).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
  const nextEvent = useMemo(() => timeline?.events.find((e) => e.date > iso), [timeline, iso])

  return (
    <div className="space-y-8">
      <section className="mx-auto max-w-3xl pt-6 text-center">
        <h1 className="text-[44px] font-semibold leading-[1.05] tracking-[-0.03em] sm:text-[52px]">Watch the law change.</h1>
        <p className="mx-auto mt-3 max-w-xl text-[19px] leading-snug text-muted">
          Every sample property, recomputed for any date. Scrub the timeline or press play to see enacted laws switch on, building by building.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <Card className="overflow-hidden">
          <div className="relative h-[560px]">
            <MapContainer bounds={REGIONS.CA} preferCanvas zoomControl={false} scrollWheelZoom className="h-full w-full">
              <TileLayer
                attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                maxZoom={16}
              />
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
                maxZoom={16}
              />
              <FitRegion region={region} />
              {data?.points.map((p) => {
                const shade = p.r[lens] ?? 'none'
                return (
                  <CircleMarker
                    key={p.id}
                    center={[p.lat, p.lon]}
                    radius={6}
                    pathOptions={{ color: '#ffffff', weight: 1.5, fillColor: RESULT_COLOR[shade], fillOpacity: 0.95 }}
                  >
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
                  </CircleMarker>
                )
              })}
            </MapContainer>

            <div className="glass pointer-events-auto absolute left-4 top-4 z-[500] w-[260px] rounded-2xl p-4 shadow-[0_8px_30px_rgba(0,0,0,0.10)]">
              <p className="eyebrow">{s.asOf}</p>
              <p className="text-[24px] font-semibold tabular-nums tracking-tight">{prettyDate}</p>
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
              <ul className="mt-3 space-y-1">
                {ORDER.filter((k) => counts[k]).map((k) => (
                  <li key={k} className="flex items-center justify-between text-[13px]">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: RESULT_COLOR[k] }} />
                      {k === 'none' ? s.none : s.results[k as Exclude<Shade, 'none'>]}
                    </span>
                    <span className="tabular-nums text-muted">{counts[k]}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="absolute right-4 top-4 z-[500]">
              <div className="glass rounded-full p-0.5 shadow-[0_4px_16px_rgba(0,0,0,0.08)]">
                <Segmented
                  value={region}
                  onChange={setRegion}
                  options={[
                    ['CA', 'California'],
                    ['NJ', 'New Jersey'],
                    ['MA', 'Massachusetts'],
                  ]}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-hairline/60 px-6 pb-5 pt-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => {
                  if (START + day * DAY >= END - 31 * DAY) setDay(0)
                  setPlaying(!playing)
                }}
                aria-label={playing ? s.pause : s.play}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-ink text-white transition hover:bg-black active:scale-95"
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
              <div className="relative flex-1 pt-3">
                <div className="pointer-events-none absolute inset-x-[11px] top-0 h-3">
                  {timeline?.events.map((e) => (
                    <span
                      key={e.rule_id}
                      title={`${e.date} · ${e.jurisdiction} · ${e.title}`}
                      className="absolute top-0 h-2.5 w-[3px] -translate-x-1/2 rounded-full"
                      style={{
                        left: `${((toMs(e.date) - START) / (END - START)) * 100}%`,
                        background: e.conflict ? '#ff9f0a' : '#0071e3',
                        opacity: e.date <= iso ? 1 : 0.35,
                      }}
                    />
                  ))}
                </div>
                <input
                  type="range"
                  className="timeline w-full"
                  min={0}
                  max={totalDays}
                  value={day}
                  onChange={(e) => {
                    setPlaying(false)
                    setDay(Number(e.target.value))
                  }}
                />
                <div className="mt-1 flex justify-between text-[11px] tabular-nums text-faint">
                  {[2024, 2025, 2026, 2027, 2028].map((y) => (
                    <span key={y}>{y}</span>
                  ))}
                </div>
              </div>
            </div>
            {nextEvent && (
              <p className="mt-3 text-[13px] text-muted">
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

        <Card className="flex max-h-[680px] flex-col overflow-hidden">
          <div className="px-6 pb-3 pt-6">
            <h3 className="text-[19px] font-semibold tracking-tight">{s.whatChanged}</h3>
          </div>
          <ol className="flex-1 overflow-y-auto px-3 pb-3">
            {timeline?.events.map((e) => {
              const past = e.date <= iso
              return (
                <li key={e.rule_id}>
                  <button onClick={() => jump(e)} className="group flex w-full gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-fill">
                    <span
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: past ? (e.conflict ? '#ff9f0a' : '#0071e3') : '#d2d2d7' }}
                    />
                    <span className={past ? '' : 'opacity-60'}>
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
