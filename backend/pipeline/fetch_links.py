"""Fetch each link-only source from the manifest exactly once (no crawling).

The starter corpus ships some sources as links only -- including the Hoboken and
Jersey City algorithmic-pricing ordinances. We read each listed page a single
time, keep the plain text with its URL and retrieval date, and mark it as a
secondary/fetched source so downstream confidence reflects that.
"""

import asyncio
import csv
import datetime as dt
import json

import httpx
from bs4 import BeautifulSoup

from .paths import EXTRA_DIR, MANIFEST

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    lines = (ln.strip() for ln in soup.get_text("\n").splitlines())
    return "\n".join(ln for ln in lines if ln)


async def fetch(client: httpx.AsyncClient, row: dict) -> dict:
    try:
        r = await client.get(row["url"], timeout=30, follow_redirects=True)
        ctype = r.headers.get("content-type", "")
        if r.status_code != 200 or "html" not in ctype:
            return {**row, "fetch_status": f"http {r.status_code} {ctype[:40]}"}
        text = html_to_text(r.text)
        if len(text) < 400:
            return {**row, "fetch_status": "too_short"}
        return {**row, "fetch_status": "ok", "text": text}
    except httpx.HTTPError as e:
        return {**row, "fetch_status": f"error {type(e).__name__}"}


async def run() -> list[dict]:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] != "ok"]
    EXTRA_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        results = await asyncio.gather(*(fetch(client, r) for r in rows))
    report = []
    for res in results:
        if res["fetch_status"] == "ok":
            body = f"SOURCE: {res['url']}\nRETRIEVED: {now}\nNOTE: fetched by team (link-only in starter pack; {res['source_type']})\n\n{res['text']}"
            (EXTRA_DIR / f"{res['doc_id']}.txt").write_text(body, encoding="utf-8")
        report.append({k: res[k] for k in ("doc_id", "jurisdictions", "url", "source_type", "fetch_status")}
                      | {"retrieved_at": now if res["fetch_status"] == "ok" else None})
    (EXTRA_DIR / "fetch_report.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    for r in asyncio.run(run()):
        print(r["doc_id"], r["jurisdictions"], r["fetch_status"], r["url"][:80])
