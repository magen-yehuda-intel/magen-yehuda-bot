# 🌙 Overnight Dashboard Improvement Plan
# Run: 2026-03-01 01:45 AM → 7:00 AM EST (5 iterations)

## Iteration Schedule

### Hour 1 (01:45-02:45) — DATA ENRICHMENT ✅ DONE
**Shipped:**
- [x] Search bar — type location/actor/keyword → instant results with fly-to + popup
- [x] Event count badges on theater buttons (ALL 48.1k, IL/GAZA 21.5k, LEBANON 4.6k, etc.)
- [x] Notes enriched for 10,703 events (all fatality events + recent OSINT)
- [x] Actor display names preserved in compact format (30 char)
- [x] Push + commit + test ✅ (`a912b33`)

### Hour 2 (02:45-03:45) — VISUAL UPGRADE ✅ DONE
**Shipped:**
- [x] 🌡️ Heatmap layer toggle (Leaflet.heat) — intensity gradient blue→cyan→yellow→red
- [x] 📊 Legend panel (bottom-left) with all marker types, closeable/reopenable
- [x] 🃏 Card-style popups — color header bar by side, emoji per event type
- [x] Dark-themed popups matching dashboard aesthetic (custom Leaflet popup CSS)
- [x] EVENT_TYPE_ICONS mapping for 10 event types
- [x] Push + commit + test ✅ (`1660ce4`)

**Note:** Marker clustering and custom SVG marker icons deferred — with 48K events, circleMarkers with canvas renderer are 10x faster than divIcons. SVG icons in `scripts/marker-icons.js` available for future use.

### Hour 3 (03:45-04:45) — ANALYTICS PANELS ✅ DONE
**Shipped:**
- [x] Key Statistics Cards — 2x2 grid: total events, fatalities, theaters, days since Oct 7
- [x] Escalation Index gauge — 7d vs 30d event rate ratio (CRITICAL/ELEVATED/NORMAL)
- [x] Daily Trend Sparkline — SVG polyline with gradient fill, last 30 days
- [x] Casualties by Force — horizontal bar chart by side with color coding
- [x] Top Actors Panel — 8 most active groups, clickable to search
- [x] Dynamically updates with filter changes
- [x] Push + commit + test ✅ (`170174b`)

### Hour 4 (04:45-05:45) — INTERACTIVITY & UX ✅ DONE
**Shipped:**
- [x] ⌨️ Keyboard shortcuts — F(ullscreen), S(earch), H(eatmap), Esc(reset), +/-(zoom), 1-9(theaters)
- [x] 🔗 URL hash state — shareable links preserving map position, time range, filters, heatmap
- [x] ⛶ Fullscreen mode — HUD+panel hide, map fills viewport, EXIT button top-right
- [x] Hash auto-loads on page open (overrides default Last 7d)
- [x] Push + commit + test ✅ (`2b08c87`)

### Hour 5 (05:45-06:45) — MOBILE & FINAL POLISH
**Goal:** Mobile must be as good as desktop

- [ ] **Mobile gesture support** — swipe between tabs
- [ ] **Mobile feed** — full-width cards with better typography
- [ ] **Mobile search** — accessible from any tab
- [ ] **PWA manifest** — add to home screen capability
- [ ] **Performance audit** — lazy load markers outside viewport
- [ ] **Final visual pass** — consistent spacing, colors, typography
- [ ] **Screenshot gallery** — capture each theater for README
- [ ] Push + commit + test
- [ ] Update SKILL.md with all new features
- [ ] Update MEMORY.md with overnight work summary
- [ ] Update memory/2026-03-01.md with detailed log

### Hour 6 (06:45+) — LIVE FEED PIPELINE
**Goal:** Make the dashboard update automatically with real-time intel

- [ ] **Design feed sync approach** — research options:
  - GitHub Actions cron pushing `docs/intel-feed.json` every hour
  - Watcher script exports last 24h `intel-log.jsonl` → `docs/intel-feed.json`
  - Dashboard JS fetches feed on load + polls every 5 min
  - Consider: GitHub Pages CDN cache (~10 min), commit frequency limits, file size
- [ ] **Build watcher export** — add feed export step to `realtime-watcher.sh` hourly cycle
  - Read `intel-log.jsonl`, filter last 24h, format as JSON array
  - Write to `docs/intel-feed.json`
  - Auto-commit + push to trigger GitHub Pages rebuild
- [ ] **Update dashboard to fetch live feed** — on load + setInterval polling
  - Merge fetched feed events into existing COMPACT_DATA events
  - Re-render feed panel with fresh data
  - Show "Last synced: X min ago" indicator
- [ ] **Handle deduplication** — feed events vs embedded COMPACT_DATA
- [ ] **Test end-to-end** — watcher → json → git push → Pages CDN → dashboard fetch
- [ ] Push + commit + test

## Subagent Tasks (parallel)
These can run independently:

1. **Data subagent**: Scrape latest OSINT from intel-log.jsonl, merge new events into strikes-data.json
2. **Icon subagent**: Generate custom SVG marker icons for each event type
3. **README subagent**: Update README.md with new dashboard screenshots + feature list
4. **ACLED subagent**: Try ACLED API again, refresh data if reachable

## Quality Gates (every iteration)
1. Rebuild standalone HTML
2. Load in browser, screenshot
3. Verify no JS errors (console check)
4. Test click interactions
5. Check file size (keep under 4MB)
6. Git commit + push
7. Verify GitHub Pages loads

## Files to Update After Each Iteration
- `scripts/strikes-dashboard.html` (template)
- `scripts/strikes-dashboard-standalone.html` (built)
- `docs/index.html` (GitHub Pages copy)
- `SKILL.md` (feature docs)
- `memory/2026-03-01.md` (daily log)
- `MEMORY.md` (long-term, final iteration only)
