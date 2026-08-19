# OOF — Open Oversight Filings

Public-record blotter of federal dockets naming **Roblox Corporation** as a party, plus the week's headlines.

Live: **https://sambas123.github.io/thats-weird/**

Unofficial. Not affiliated with Roblox or NCMEC. Not a safety product. Not legal advice.

The ticker is **$OOF**. The letters are the product: open filings, counted in public.

## What it counts

| Field | Source | Query |
|---|---|---|
| Docket total / 7d / 30d | [CourtListener](https://www.courtlistener.com/) | `party:"Roblox Corporation"` |
| Headlines, 7 days | Google News RSS | `Roblox (lawsuit OR grooming OR eSafety OR NCMEC OR Senate)` |
| On-the-record chips | Hand-cited news / Senate / IR | see `scripts/refresh_tape.py` → `RECORD` |

The 1,200+ hit count for a raw `Roblox` search includes junk (unrelated bankruptcies, etc.). The party query is the honest number.

## How it updates

GitHub Action, about once an hour (`scripts/refresh_tape.py` → `tape.json`). If a source fails, the last good slice stays.

One request set per hour. Do not turn this into a live proxy of CourtListener.

## Run locally

```bash
python3 scripts/refresh_tape.py
python3 -m http.server 8765
# open http://127.0.0.1:8765
```

## After a ticker exists

Set `token` in `tape.json` (the refresh script preserves it):

```json
"token": { "symbol": "OOF", "mint": "<address>" }
```

Custom domain later is a DNS CNAME onto this same Pages site. Do not rebuild.
