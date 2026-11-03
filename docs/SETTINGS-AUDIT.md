# Magen settings integration audit

## Scope and evidence

The main and CENTCOM pages were audited together with Aetherwatch's deployed embed contract. Static handler inventory and browser behavior are separate evidence. `tests/browser-settings-audit.js` is the executable browser acceptance pass; its result must be captured after publication before declaring the full audit live-verified.

## Merged into one dashboard

- `index.html` and `centcom.html` are identical; both load `dashboard-controls.js`.
- Both retain feed search (including Hebrew acronym normalization), safer news click binding, keyboard selection and brief font controls.
- Selected news/asset locations focus the visible renderer. Selected areas survive feed/settings updates; Unlock returns to the theater view.
- Background globe updates omit camera, rather than resetting navigation.

## Shared controls repaired

- Layer search hides nonmatching rows; empty search restores them.
- All strike-window selectors contain 24h / 48h / 7d and synchronize.
- Reset defines every layer state, clears selected zone/filter/preferences and restores the sparse 3D default.
- Clear removes overlays, event highlight and missile animation.
- Presets refresh button state and invoke required loaders.
- Aircraft and fire controls share cycling semantics on sidebar/mobile/desktop.
- Mobile status reflects real state, including the three missile modes.
- Feed filter results update 2D OSINT and 3D news pins even for zero matches.
- Category counts respect time/search and preserve category selection.
- Feed time changes do not clear brief time selection.
- Sidebar/feed/brief open-state indicators reconcile when panels close.
- Asset inventory no longer truncates at 100; infrastructure assets and totals are included.
- Iran energy and Gulf energy are separate layers. Iran-only does not enable Gulf facilities.
- Aircraft and AIS availability are not portrayed as measured zero; provider AIS count remains unknown.
- Explicit missile OFF is not overwritten by fresh critical events.
- Proxy pin colors use `iran_proxy`; finite zero latitude/longitude are valid.
- Historical strike tooltips are replaced with selected-window wording.
- Save includes renderer, layers/modes, display, filters/search, selected zone and time window.
- Geolocation forwards to the visible renderer; errors are surfaced.
- The legend changes with renderer instead of describing the hidden map.

## Native 3D support

- Satellite / street imagery and all seven sensor styles.
- Sparse / balanced / off detection labels through an extended acknowledged embed contract.
- Regional political areas for Iran, Israel, Lebanon, Syria, Iraq, Jordan, Saudi Arabia, UAE, Yemen, Oman, Kuwait and Qatar. These are annotated country geometries, not a worldwide border-only tile layer.
- Filtered news pins, capped at 12 locations; coincident reports share one identified pin and remain accessible through card pagination. Selected news retains its identity through zone focus.
- ALL or military aircraft, live provider AIS vessels, earthquakes, optional provider military-site inventory.
- Parent origin AND source-window checks; command errors surfaced; unavailable viewer can fall back to 2D.

## Exact overlays retained in 2D, explicitly routed

These controls are labeled 2D and switch to that renderer. They are not represented as equivalent native 3D provider layers:

- US bases / military inventory.
- Iran infrastructure, nuclear, missile, naval, air-defense, air-base and IRGC sites.
- Iran energy and separate Gulf energy.
- SAM range rings, waterways and static patrol routes.
- Static GPS-interference zones.
- Magen siren points, recent strikes and thermal/seismic correlations.
- Exact fire-age filtering and civilian-only aircraft filtering.
- Missile path/animation rendering and strike time windows.
- English-label Esri Dark Gray Base + Reference and VIIRS imagery. Standard OpenStreetMap raster used local-language names; the replacement English labels were visually verified over the Gulf without an API-key watermark.

## Data limitations, not silently 'fixed'

- 2D naval positions and GPS-interference areas are static estimates. The 3D vessel feed is a different live provider, not proof the static estimates are live.
- Military/energy/infrastructure inventory remains an archived snapshot, not current operational status.
- A correlation score is not independent confirmation of a strike.
- `gev:ready` is not proof satellite imagery rendered. Browser visual verification must be reported independently from protocol acknowledgement.

## Verification record

- Python freshness/publication tests: 9 passed during implementation.
- Node event-zone tests: both page entry points passed.
- Node status/inline-script parsing tests passed.
- Shared adapter syntax check passed.
- Browser preview: 14 settings/preset/reset/routing assertions passed against live data before publication. This was an injected QA preview, not production deployment evidence.
- Final deployed browser acceptance: 51/51 checks passed. Globe acknowledged style/map/detection/annotation steps successfully, and 3D satellite globe imagery was visually observed.
- Visual follow-up repairs: install prompt moved to the sidebar to avoid covering map controls; key-required 2D tiles replaced; theater camera changed to a top-down regional view. Final deployed control recheck passed 51/51; the mobile drawer and selected-zone map were visually inspected. See `settings-audit-receipt.json` for executable-check results.
- Aetherwatch protocol implementation: commit `9d282fdc4a1d885164c4521319870d7ec20477d2`, deployed revision `aetherwatch-globe--0000002`; exact delivered bundle SHA256 independently matched `68d7237fca182ec65298e245778e6a98e5ca13632fbb1fa22a6d04097e5ed5be`.


## Pin-to-news and renderer recovery release

- The original pins were pointer-transparent SVG annotations, not selectable Cesium entities. They had labels but no reverse news identity.
- `news-pin-model.js` groups reports by coordinates and emits an opaque `clientId`. `news-pin-bubbles.js` resolves selection only against host-owned current news, checking both origin and source window. Text is rendered as text; report links allow only HTTP(S).
- A real mouse click, actual phone-size touch tap, and Enter activation on the delivered SVG hit target each opened the expected report. The mobile card was visually inspected with headline, source, timestamp, original link, close and pagination.
- The deployed settings regression passed **51/51**, news-card/security checks **10/10**, and recovery/security checks **7/7**. Three actual 2D→3D cycles resumed frames without context loss or error panels.
- `map-render-recovery.js` consumes the actual globe render-error notification, preserves bounded diagnostics, returns to usable 2D, destroys the failed iframe and offers a manual fresh-renderer retry. Retry was verified against a fresh matching command/acknowledgement ID.
- An explicitly labeled test error was raised through the deployed Cesium scene's real `renderError` event. Its cross-frame notification triggered fallback and fresh retry. This is a recovery test, **not reproduction of the user's fragment-shader compilation failure**. The underlying compiler failure remains unexplained; no guessed GPU flags were applied.
- Receiver source `a38a1805963bc2a9550595a0f505e21b6884ccc0`, Azure revision `aetherwatch-globe--0000003`; delivered bundle SHA256 `90cc25fcf615003f2736eb80b064457cf4da4ca5944a531fb1636cbbdf65729d` independently verified. Host source `a230721ca065e5be8b63fd17ae25d5edc84dca89`.
- Executable results: `pin-recovery-receipt.json`. Tests: `test-news-pin-bubbles.js`, `browser-news-bubbles.js`, `browser-render-recovery.js` under `tests/`.
