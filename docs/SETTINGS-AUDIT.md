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
- Filtered news pins, capped visibly at 12 newest matches; selected event gets a single selected pin.
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
- CARTO and VIIRS imagery.

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
- Full deployed browser acceptance and visual verification: pending coordinated globe deployment.
