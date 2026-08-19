#!/usr/bin/env python3
"""Refresh tape.json from public CourtListener + Google News RSS.

One hourly GitHub Action. Cache locally; do not hammer sources.
If a source fails, keep the previous slice of the tape.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAPE_PATH = ROOT / "tape.json"

UA = "OOF-tape/0.1 (+https://sambas123.github.io/thats-weird; Open Oversight Filings)"

TOKEN = {
    "symbol": "OOF",
    "mint": "8W3uULPKMWvrJYmf2viFE75T6i15H59r6uzs9X4upump",
    "pump": "https://pump.fun/coin/8W3uULPKMWvrJYmf2viFE75T6i15H59r6uzs9X4upump",
}
CL_BASE = "https://www.courtlistener.com/api/rest/v4/search/"
CL_QUERY = 'party:"Roblox Corporation"'
NEWS_QUERY = "Roblox (lawsuit OR grooming OR eSafety OR NCMEC OR Senate) when:7d"

# Hand-cited public facts. Edit here; the page just renders them.
RECORD = [
    {
        "label": "NCMEC reports filed by Roblox",
        "value": "24,522 → 65,381",
        "period": "2024–2025",
        "source": "U.S. Senate Judiciary",
        "url": "https://www.judiciary.senate.gov/press/rep/releases/grassley-releases-new-and-disturbing-information-on-online-child-exploitation-presses-tech-giants-for-answers",
    },
    {
        "label": "RBLX after age-check bookings miss",
        "value": "−18%",
        "period": "2026-05-01",
        "source": "CNBC",
        "url": "https://www.cnbc.com/2026/05/01/roblox-rblx-stock-child-safety-earnings.html",
    },
    {
        "label": "Age-checked DAU under 13",
        "value": "35%",
        "period": "as of 2026-01-31",
        "source": "Roblox shareholder letter",
        "url": "https://s27.q4cdn.com/984876518/files/doc_financials/2026/q1/Q1-2026-Earnings-Shareholder-Letter.pdf",
    },
    {
        "label": "Australia eSafety undertaking",
        "value": "issued",
        "period": "2026-08-19",
        "source": "The Guardian / Reuters",
        "url": "https://www.theguardian.com/australia-news/2026/aug/20/roblox-esafety-commissioner-children-adults-ntwnfb",
    },
    {
        "label": "AL + WV child-safety settlements",
        "value": "$23M+",
        "period": "2026-04",
        "source": "Reuters",
        "url": "https://www.reuters.com/legal/government/roblox-pay-23-million-alabama-west-virginia-settle-child-safety-investigations-2026-04-21/",
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_prev() -> dict:
    if not TAPE_PATH.exists():
        return {}
    try:
        return json.loads(TAPE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def fetch(url: str, timeout: int = 30) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def cl_search(q: str, filed_after: str | None = None, page_size: int = 20) -> dict:
    params = {
        "type": "d",
        "q": q,
        "order_by": "dateFiled desc",
        "page_size": str(page_size),
    }
    if filed_after:
        params["filed_after"] = filed_after
    url = CL_BASE + "?" + urllib.parse.urlencode(params)
    return json.loads(fetch(url))


def normalize_docket(row: dict) -> dict:
    path = row.get("docket_absolute_url") or ""
    return {
        "date_filed": row.get("dateFiled"),
        "case_name": (row.get("caseName") or "").strip(),
        "docket_number": row.get("docketNumber") or "",
        "court": row.get("court_citation_string") or row.get("court") or "",
        "url": ("https://www.courtlistener.com" + path) if path else "",
    }


def pull_dockets() -> dict:
    today = date.today()
    total = cl_search(CL_QUERY)
    week = cl_search(CL_QUERY, filed_after=(today - timedelta(days=7)).isoformat())
    month = cl_search(CL_QUERY, filed_after=(today - timedelta(days=30)).isoformat())
    latest = [normalize_docket(r) for r in (total.get("results") or [])[:8]]
    latest = [d for d in latest if d["case_name"]]
    return {
        "query": CL_QUERY,
        "source": "https://www.courtlistener.com/",
        "search_url": "https://www.courtlistener.com/?type=d&q="
        + urllib.parse.quote(CL_QUERY)
        + "&order_by=dateFiled+desc",
        "total": int(total.get("count") or 0),
        "filed_7d": int(week.get("count") or 0),
        "filed_30d": int(month.get("count") or 0),
        "latest": latest,
    }


def parse_rss_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            return iso(datetime.strptime(raw, fmt))
        except ValueError:
            continue
    return raw


def pull_news() -> dict:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {
            "q": NEWS_QUERY,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
    )
    xml = fetch(url)
    root = ET.fromstring(xml)
    seen: set[str] = set()
    items: list[dict] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        source = ""
        src_el = item.find("{http://www.google.com/schemas/sitemap-news/0.9}news")
        # Google puts the outlet after an em dash in the title.
        outlet = ""
        if " - " in title:
            title, outlet = title.rsplit(" - ", 1)
        items.append(
            {
                "title": title.strip(),
                "outlet": outlet.strip(),
                "url": link,
                "published": parse_rss_date(item.findtext("pubDate")),
            }
        )
        if len(items) >= 8:
            break
    return {
        "query": NEWS_QUERY,
        "source": "Google News RSS",
        "hits_7d": len(root.findall("./channel/item")),
        "latest": items,
    }


def merge(prev: dict, dockets: dict | None, news: dict | None, errors: list[str]) -> dict:
    prev_d = prev.get("dockets") if isinstance(prev.get("dockets"), dict) else {}
    prev_n = prev.get("news") if isinstance(prev.get("news"), dict) else {}
    token = TOKEN or prev.get("token")
    return {
        "as_of": iso(utc_now()),
        "token": token if token else None,
        "dockets": dockets or prev_d,
        "news": news or prev_n,
        "record": RECORD,
        "errors": errors,
    }


def write_tape(tape: dict) -> None:
    tmp = TAPE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tape, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(TAPE_PATH)


def main() -> int:
    prev = load_prev()
    errors: list[str] = []
    dockets = news = None

    try:
        dockets = pull_dockets()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        errors.append(f"courtlistener: {exc}")

    try:
        news = pull_news()
    except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as exc:
        errors.append(f"news: {exc}")

    if dockets is None and news is None and not prev:
        print("refresh failed with no prior tape", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    tape = merge(prev, dockets, news, errors)
    write_tape(tape)
    d = tape.get("dockets") or {}
    n = tape.get("news") or {}
    print(
        f"ok dockets={d.get('total')} 7d={d.get('filed_7d')} "
        f"news7d={n.get('hits_7d')} errors={len(errors)}"
    )
    for line in errors:
        print("warn", line, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
