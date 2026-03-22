# UI/UX Improvement Plan — 3 Hours (03:39-06:39 EST)

## Hour 1: Custom SVG Icons + Larger Defaults (03:39-04:39)
**Goal:** Replace boring circle markers with beautiful, distinctive SVG icons per event type

### Tasks
1. **Design 10 custom SVG marker icons** at 32×32px (up from 24px):
   - 💥 `Shelling/artillery/missile attack` → Red starburst explosion
   - ✈️ `Air/drone strike` → Blue jet silhouette with impact flash
   - ⚔️ `Armed clash` → Crossed swords with shield
   - 🎯 `Attack` → Red crosshair/target reticle
   - 💣 `Remote explosive/landmine/IED` → Classic bomb with fuse
   - 📡 `Location mention in OSINT` → Cyan radar pulse rings
   - 💀 `Suicide bomb` → Skull with blast ring
   - 🔥 `Possible strike (FIRMS)` → Fire/flame icon (orange)
   - 🌡️ `Thermal anomaly (FIRMS)` → Heat wave icon (dimmer orange)
   - 🚨 `Siren alert` → Siren/alert bell icon
2. **Replace `L.circleMarker` with `L.marker` + `L.divIcon`** using inline SVG data URLs
3. **Scale icons by fatalities/importance** — base 24px, scales up to 48px for high-casualty events
4. **Increase default marker scale** from 1× to 1.5×
5. **Increase default font scale** from 1× to 1.15×
6. **Make MARKER_STEPS and FONT_STEPS start higher**: `[1, 1.5, 2, 2.5, 3, 4]` and `[1, 1.15, 1.3, 1.5, 1.7, 2]`

## Hour 2: Panel & Feed UI Overhaul (04:39-05:39)
**Goal:** Make the side panel beautiful and readable

### Tasks
1. **Increase all font sizes:**
   - Section titles: 8px → 11px
   - Body text: 9px → 11px
   - Stats: 9px → 12px
   - Feed items: 10px → 12px
   - Theater/phase buttons: 9px → 11px
   - Timeline title: 8px → 10px
   - HUD stats: 9px → 11px
   - Logo: 11px → 14px
2. **Event type legend with SVG previews** — show actual icon next to each type name
3. **Feed cards redesign:**
   - Colored left border by event type
   - Larger source name (bold, colored)
   - Better spacing between cards
   - Event type mini-icon next to source
4. **Force disposition bars** — increase height, add gradient fills
5. **Theater buttons** — larger padding, badge icons bigger
6. **Panel width** — increase default from 320px to 360px
7. **HUD bar height** — increase from 40px to 48px

## Hour 3: Mobile UX + Visual Polish (05:39-06:39)
**Goal:** Mobile-first refinements and overall visual consistency

### Tasks
1. **Mobile font sizes bumped** — all mobile text +2px
2. **Mobile feed cards** — larger touch targets, bigger icons
3. **Mobile tab bar** — taller (44px → 52px), bigger icons (16px → 22px)
4. **Popup improvements:**
   - Larger popups with better padding
   - Event type SVG icon in popup header
   - Larger font in popup body
5. **Tooltip improvements** — larger, higher contrast
6. **Legend redesign** — use actual SVG icons instead of colored dots
7. **Smooth animations** — marker hover glow effect
8. **Loading screen** — brief branded splash while data loads
9. **Final build + deploy** to GitHub Pages

## Design Principles
- NATO APP-6 inspired iconography (recognizable military symbology)
- High contrast on dark backgrounds (#0a0e17)
- Distinct silhouettes — must be identifiable at 20px
- Color-coded by actor side (Israel blue, Iran red, proxy orange, US navy blue)
- Size communicates severity/casualties
- No emoji — pure SVG for crisp rendering at all scales
