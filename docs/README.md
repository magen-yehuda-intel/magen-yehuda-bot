# docs/ — Dual Purpose Directory

This folder serves two purposes:

## 1. GitHub Pages Static Site
GitHub Pages is configured to serve from `docs/`. These are the live dashboard files:
- `index.html` — Main dashboard
- `centcom.html` — CENTCOM operations view
- `hormuz.html` — Strait of Hormuz monitoring
- `strikes.html` — Strike correlation map
- `v2-data.js` — Dashboard data layer
- `sw.js`, `manifest.json` — PWA support
- `*.json` feeds — `intel-feed.json`, `live-events.json`, `oref-alerts.json`, etc.
- `data/` — Static data assets for the dashboard
- `icons/` — Map marker icons and UI assets

## 2. Project Documentation
- `ARCHITECTURE.md` — Full system architecture
- `OPENSPEC.md` — Dashboard UI specification
- `TROUBLESHOOTING.md` — Common issues and fixes
- `INTELLIGENCE_METHODOLOGY.md` — OSINT collection methodology

**Do not reorganize this folder** — the GitHub Pages deployment depends on this structure.
