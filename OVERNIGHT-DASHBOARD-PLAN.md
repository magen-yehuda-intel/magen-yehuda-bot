# 🌙 Overnight Dashboard Improvement Plan
# Run: 2026-03-01 01:45 AM → 7:00 AM EST (5 iterations)

## Iteration Schedule

### Hour 1 (01:45-02:45) — DATA ENRICHMENT
**Goal:** Surface the rich ACLED data that's buried

- [ ] Extract `actor1_display` and `actor2_display` from ACLED for ALL events (not just recent)
  - ACLED has detailed actor names: "Islamic State (IS)", "Israeli Air Force", "Hezbollah"
  - Currently showing generic "ISRAEL (IDF)" etc.
- [ ] Add `notes` for ALL ACLED events to compact data (not just last 90 days)
  - Truncate to 100 chars, only for events with notes
  - This gives every marker a story when clicked
- [ ] Add event count badges to theater buttons (e.g., "🇱🇧 LEBANON (4,609)")
- [ ] Search bar — type location/actor/keyword → filter + fly to results
- [ ] Push + commit + test

### Hour 2 (02:45-03:45) — VISUAL UPGRADE  
**Goal:** Military-grade icons and markers

- [ ] Custom SVG markers per event type:
  - 💥 Shelling/artillery → explosion icon
  - ✈️ Air/drone strike → aircraft icon  
  - ⚔️ Armed clash → crossed swords
  - 🎯 Attack → target
  - 💣 Remote explosive/IED → bomb
  - 📡 OSINT mention → satellite dish
  - 💀 Suicide bomb → skull
- [ ] Pulsing animation for events < 48h old
- [ ] Marker clustering with custom cluster icons showing count + dominant type
- [ ] Heatmap layer toggle (Leaflet.heat)
- [ ] Legend panel showing all marker types
- [ ] Better popup design — card-style with header color bar by side
- [ ] Push + commit + test

### Hour 3 (03:45-04:45) — ANALYTICS PANELS
**Goal:** Make the dashboard tell a story with numbers

- [ ] **Casualty Tracker** — running total by side, country, time period
  - Bar chart or sparkline showing daily fatalities
- [ ] **Escalation Index** — computed score based on event frequency + severity
  - Visual meter/gauge in header bar
- [ ] **Top Actors Panel** — most active groups with event counts
  - Clickable → filter map to that actor
- [ ] **Daily Event Trend** — mini sparkline chart in header showing last 30 days
- [ ] **Key Statistics Cards** — prominent numbers at top:
  - Total strikes, Total KIA, Active theaters, Days since Oct 7
- [ ] Push + commit + test

### Hour 4 (04:45-05:45) — INTERACTIVITY & UX
**Goal:** Polish to production quality

- [ ] **Keyboard shortcuts** — T(heater), F(eed), S(earch), Esc(reset), +/- zoom
- [ ] **URL hash state** — save current view (theater, time range, filters) in URL
  - Share specific dashboard states via link
- [ ] **Hover tooltips** — show mini info on marker hover (not just click)
- [ ] **Fullscreen button** — hide header for max map space
- [ ] **Auto-refresh indicator** — "Last updated: X min ago" in header
- [ ] **Smooth transitions** — animate marker appearance on filter change
- [ ] **Loading skeleton** — show placeholder while data loads
- [ ] **Right-click context menu** on map — "What happened here?" radius search
- [ ] Push + commit + test

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
