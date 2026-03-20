# BT Live Server Design — TBD (DO NOT IMPLEMENT WITHOUT APPROVAL)

_Created: Mar 19, 2026_
_Status: PLANNING — awaiting Idan's go-ahead_

## Summary
Unify Magen Yehuda watcher + BT geo overlay into a single FastAPI server (`magen-yehuda-server`) with real-time futures data from IB Gateway and SSE push to browser dashboards.

## Key Decisions
1. **IB Gateway** (port 4002, ib_insync) for real-time CL futures — tvDatafeed as fallback
2. **lightweight-charts** (TV's open-source lib) for charting — same look, our data, no restrictions
3. **Immediate LLM enrichment** for mkt≥8 events, batch hourly for mkt<8
4. **Single FastAPI process**, asyncio tasks — no microservices needed
5. **SSE** (not WebSocket) — simpler, sufficient for server→browser push
6. **State persistence** — disk files on shutdown, restore on startup

## Architecture
See ASCII diagram in chat session (Mar 19 ~3:00 PM ET) or memory/2026-03-19.md

## Process Architecture
- Port 8400
- asyncio tasks: scan_osint (30s), scan_sensors (2min), scan_cyber (60s), correlate (30s), enrich_batch (5min), ib_stream (live), dispatch (live), db_sync (5min), cleanup (1h)
- Endpoints: /health, /events, /candles, /stream/events (SSE), /stream/candles (SSE), /watchlist, /metrics

## Data Flow (single event lifecycle)
1. Scanner picks up event → dedup → event bus
2. Geocode via LOC_MAP
3. Keyword fast-path severity estimate (free)
4. If mkt≥8 → immediate LLM enrich; else → batch queue
5. Enriched event → SSE push + Telegram dispatch + BT alerts + Azure Table + JSONL

## Dashboard
- lightweight-charts with live candle updates via SSE
- Geo markers, red volume bars, toast notifications
- Watchlist with geo-flash (URA, XLE, LNG, INSW, etc.)
- Geo intel panel (scrollable, impact≥8)

## Open Questions
- Symbol switching UI (multi-symbol support? tabs?)
- Historical backfill on dashboard load (how many bars?)
- Auth for server endpoints?
- Run as launchd service or keep ctl.sh?
- MY dashboard: migrate from GitHub Pages static to also use SSE?

## Related Files
- Current watcher: `scripts/realtime-watcher.sh`
- Current scanners: `scripts/scan-*.py`
- Current dispatch: `scripts/dispatch.py`
- BT alerts: `scripts/bt-geo-alerts.py`
- Dashboard mockup: `docs/bt-geo-overlay-chart.html`
- Enrichment: `scripts/enrich-intel.py`
