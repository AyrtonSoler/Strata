export async function api<T>(path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // Network-level failure: the API server is down or the page wasn't served by Vite/Vercel.
    throw new Error('Can’t reach the Strata API. Start it with `npm run dev` from the repo root, then reload.')
  }
  if (!res.ok) {
    const text = await res.text()
    let detail = text
    try {
      detail = JSON.parse(text).detail ?? text
    } catch {
      /* plain-text error */
    }
    if (res.status >= 500 && /ECONNREFUSED|proxy/i.test(text)) {
      throw new Error('The Strata API isn’t running. Start it with `npm run dev` from the repo root, then reload.')
    }
    throw new Error(String(detail))
  }
  return res.json() as Promise<T>
}
