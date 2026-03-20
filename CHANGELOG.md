
## 2026-03-19 — LLM Intel Enrichment Pipeline

### New Features
- **🧠 `enrich-intel.py`**: Batch LLM enrichment pipeline using Azure OpenAI gpt-5-mini
  - Pre-filters noise (prayers, spam, short posts) — only enriches conflict-relevant events
  - Extracts per event: location + coords, attacker, target_country, target_type, attack_type, weapon, severity, summary
  - **Breaking news detection**: `is_breaking` flag distinguishes new events from commentary/analysis
  - **Market impact scoring**: 0-10 scale (10=Hormuz blocked, 0=commentary) with affected sector tags
  - **Market sectors**: oil, natural_gas, defense, shipping, crypto, equities, bonds, insurance
  - Expanded target types: `gas_infrastructure`, `ship`, `missile_launcher`, `pipeline`, `refinery`, `lng_terminal`
  - Expanded weapons: `torpedo`, `naval_mine`
  - Dual storage: writes to Azure Table DB + local `enriched-intel.jsonl`
  - Dedup via `enriched-ids.json` — won't reprocess already-enriched events
  - Hourly cron (top of hour, 2h lookback, limit 100 events)

### Bug Fixes
- **Yanbu location bug**: Added missing Saudi cities to `export-feed.py` LOC_MAP (Yanbu, Jeddah, Riyadh, Abqaiq, Jubail, Dammam). Events mentioning "Yanbu port in Saudi Arabia" were geocoded to Iran centroid because "Iran" keyword matched before "Saudi" fallback.

### Infrastructure
- **DB repopulated**: Pushed 4,077 JSONL events into Azure Table Storage after `publicNetworkAccess: Disabled` was blocking local writes. Events for Mar 15-19 went from 2,669 → 6,452.
- **DB auth fixed**: Root cause was storage account `publicNetworkAccess: Disabled` — Entra ID RBAC was correctly assigned but all requests from local Mac were rejected at network level.

## 2026-03-09 — CENTCOM Dashboard Major Update

### New Features
- **🛰️ Recon Satellite Tracking**: 10 imaging/recon satellites (WorldView-3, Pléiades Neo, EROS C3, KOMPSAT-3A, Sentinel-2A/2B, PRAETORIAN SDA, SAPPHIRE) with real-time SGP4 orbital propagation via satellite.js, ground tracks (±15 min), imaging swath overlays, green pulse when over ME
- **🚢 US Navy Fleet Layer**: 11 vessels (CVN-75 Truman, CVN-70 Vinson, LHD-5 Bataan, CG-64, DDG-55/107/109, SSGN-728 Florida, USNS Supply, INS Magen, INS Dolphin) with OSINT-based positions
- **📡 GPS Jamming Zones**: 9 known interference areas (Eastern Med, Hormuz, Tehran, Isfahan, Bushehr, Yemen, Libya, Sinai) with severity levels and pulsing high zones
- **🔥 Fire Mode Cycling**: 5-mode button (OFF/<1H/1-3H/3-6H/ALL) with colored 🔥 icon feedback
- **🚨 Pikud HaOref History**: Click the Oref banner → transparent overlay showing last 3 siren alerts
- **✈️ Aircraft from own API**: Switched from OpenSky (no CORS) to our API — 435 planes with airline, type, from/to airports

### Performance
- **Viewport-based rendering**: OSINT + fire markers only render within 2x viewport buffer, re-render on pan/zoom (300ms debounce)

### UI/UX
- Title changed to "U.S. & ISRAEL vs. IRAN"
- OSINT events OFF by default (reduce visual noise)
- Base labels ON by default
- Fires default to 1-3H timeframe
- Ticker 2x slower (48s/item, min 360s cycle) + click to pause/resume
- Fire button icon: 🔥 with colored glow (red/orange/grey) per mode instead of ⬤ circle

### Bug Fixes
- Satellites: embedded TLE data (CelesTrak has no CORS headers)
- Aircraft: routed through own API (OpenSky has no CORS headers)
- Trail loading: CORS proxy fallback for OpenSky tracks API
