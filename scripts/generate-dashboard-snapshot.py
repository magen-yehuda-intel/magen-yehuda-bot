#!/usr/bin/env python3
"""
Generate a CENTCOM theater dashboard snapshot image for Telegram dispatch.

Pulls live data from the Magen Yehuda API:
- NASA FIRMS fires (≥15 MW)
- USGS seismic events
- Strike correlations (scored)
- Active sirens

Renders a dark-themed satellite map with overlays and summary HUD.

Usage:
    python3 generate-dashboard-snapshot.py <output.png> [--caption-file <caption.txt>]
"""

import sys
import os
import json
import math
import io
import urllib.request
import time
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

API_URL = "https://magen-yehuda-api.blackfield-628213bb.eastus.azurecontainerapps.io"
DASHBOARD_URL = "https://magen-yehuda-intel.github.io/magen-yehuda-bot/centcom.html"

# Theater bounds (wider than Iran-only — matches centcom.html default view)
MAP_WEST = 24.0
MAP_EAST = 64.0
MAP_SOUTH = 12.0
MAP_NORTH = 42.0

ESRI_SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILE_SIZE = 256
ZOOM = 5
IMG_WIDTH = 1200
IMG_HEIGHT = 800

# Score thresholds (match centcom.html model)
SCORE_PROBABLE = 70
SCORE_POSSIBLE = 45
SCORE_SUSPICIOUS = 25

# FRP thresholds
MIN_FIRE_FRP = 10
CORRELATION_MIN_FRP = 15
SPATIAL_MAX_KM = 30
TEMPORAL_MAX_SEC = 1800

# Colors (RGBA)
COLOR_FIRE_HOT = (255, 34, 0, 230)
COLOR_FIRE_WARM = (255, 136, 0, 180)
COLOR_FIRE_COOL = (204, 136, 0, 120)
COLOR_QUAKE = (0, 150, 255, 200)
COLOR_QUAKE_SHALLOW = (180, 0, 255, 220)
COLOR_STRIKE_PROBABLE = (255, 0, 64, 240)
COLOR_STRIKE_POSSIBLE = (255, 102, 0, 200)
COLOR_STRIKE_SUSPICIOUS = (138, 122, 64, 120)
COLOR_SIREN = (255, 0, 0, 255)
COLOR_HUD_BG = (10, 10, 26, 200)
COLOR_HUD_TEXT = (255, 255, 255, 230)
COLOR_HUD_RED = (255, 0, 64, 255)
COLOR_HUD_DIM = (180, 180, 200, 160)

KNOWN_SITES = [
    {"name": "Natanz", "lat": 33.72, "lon": 51.72, "icon": "☢️"},
    {"name": "Fordow", "lat": 34.88, "lon": 51.59, "icon": "☢️"},
    {"name": "Isfahan", "lat": 32.65, "lon": 51.68, "icon": "☢️"},
    {"name": "Bushehr", "lat": 28.83, "lon": 50.89, "icon": "☢️"},
    {"name": "Tehran", "lat": 35.69, "lon": 51.39, "icon": "🏛"},
    {"name": "Baghdad", "lat": 33.31, "lon": 44.37, "icon": "🏛"},
    {"name": "Riyadh", "lat": 24.71, "lon": 46.68, "icon": "🏛"},
    {"name": "Tel Aviv", "lat": 32.08, "lon": 34.78, "icon": "🏛"},
    {"name": "Bandar Abbas", "lat": 27.19, "lon": 56.27, "icon": "⚓"},
    {"name": "Kharg Island", "lat": 29.23, "lon": 50.31, "icon": "🛢"},
    {"name": "Strait of Hormuz", "lat": 26.56, "lon": 56.25, "icon": "🚢"},
]

# ═══════════════════════════════════════════════════════════
# TILE MATH
# ═══════════════════════════════════════════════════════════

def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y

def lat_lon_to_pixel(lat, lon, zoom, origin_x, origin_y, scale_x, scale_y):
    n = 2 ** zoom
    px = (lon + 180) / 360 * n * TILE_SIZE - origin_x * TILE_SIZE
    lat_rad = math.radians(lat)
    py = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n * TILE_SIZE - origin_y * TILE_SIZE
    return int(px * scale_x), int(py * scale_y)

def download_tile(z, x, y):
    url = ESRI_SAT_URL.format(z=z, x=x, y=y)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaIntel/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGBA")
    except Exception:
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (10, 10, 26, 255))

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ═══════════════════════════════════════════════════════════
# API FETCH
# ═══════════════════════════════════════════════════════════

def api_get(endpoint):
    url = f"{API_URL}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaIntel/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠️ Failed to fetch {endpoint}: {e}", file=sys.stderr)
        return None

def fetch_fires():
    data = api_get("/api/fires")
    if not data:
        return []
    fires = data if isinstance(data, list) else data.get("fires", data.get("events", []))
    result = []
    for f in fires:
        frp = float(f.get("frp", 0) or 0)
        if frp < MIN_FIRE_FRP:
            continue
        lat, lon = f.get("lat"), f.get("lon")
        if not lat or not lon:
            continue
        ts = 0
        acq = f.get("acq", "")
        if acq:
            try:
                m = __import__("re").match(r"(\d{4})-(\d{2})-(\d{2})\s*(\d{1,2})(\d{2})?", acq)
                if m:
                    h, mn = int(m.group(4)), int(m.group(5) or 0)
                    ts = datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)} {h:02d}:{mn:02d}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()
            except:
                pass
        result.append({"lat": float(lat), "lon": float(lon), "frp": frp, "ts": ts, "confidence": f.get("confidence", "?")})
    return result

def fetch_seismic():
    data = api_get("/api/intel-feed?hours=24&limit=2000")
    if not data:
        return []
    events = data if isinstance(data, list) else data.get("events", [])
    quakes = []
    for e in events:
        if "earthquake" not in (e.get("sub_event_type", "") + e.get("type", "") + e.get("notes", "")).lower():
            continue
        lat, lon = e.get("lat"), e.get("lon")
        if not lat or not lon:
            continue
        quakes.append({
            "lat": float(lat), "lon": float(lon),
            "mag": float(e.get("magnitude", e.get("mag", 0)) or 0),
            "depth": float(e.get("depth", 999) or 999),
            "time": float(e.get("timestamp", e.get("ts", 0)) or 0),
            "place": e.get("location", e.get("place", ""))
        })
    return quakes

def fetch_sirens():
    data = api_get("/api/oref/history?limit=5")
    if not data:
        return []
    return data if isinstance(data, list) else data.get("alerts", [])

# ═══════════════════════════════════════════════════════════
# CORRELATION ENGINE (mirrors centcom.html model)
# ═══════════════════════════════════════════════════════════

def score_correlation(q, f, dist, time_diff):
    score = 0
    t_min = time_diff / 60
    # Spatial
    if dist <= 5: score += 30
    elif dist <= 15: score += 20
    else: score += 10
    # Temporal
    if t_min <= 5: score += 25
    elif t_min <= 15: score += 20
    else: score += 10
    # Seismic depth
    if q["depth"] < 5: score += 15
    elif q["depth"] < 10: score += 8
    # Magnitude
    if 2.0 <= q["mag"] <= 4.5: score += 10
    elif q["mag"] > 4.5: score += 5
    # Thermal
    if f["frp"] >= 50: score += 15
    elif f["frp"] >= 25: score += 10
    elif f["frp"] >= 15: score += 5
    # Confidence
    conf = f.get("confidence", "?")
    if conf == "h" or (isinstance(conf, (int, float)) and conf >= 80): score += 5
    return score

def compute_correlations(fires, quakes):
    correlations = []
    matched_fires = set()
    # Paired
    for q in quakes:
        for f in fires:
            if f["frp"] < CORRELATION_MIN_FRP: continue
            td = abs(q["time"] - f["ts"])
            if td > TEMPORAL_MAX_SEC: continue
            dist = haversine(q["lat"], q["lon"], f["lat"], f["lon"])
            if dist > SPATIAL_MAX_KM: continue
            sc = score_correlation(q, f, dist, td)
            correlations.append({"type": "paired", "lat": (q["lat"]+f["lat"])/2, "lon": (q["lon"]+f["lon"])/2, "score": sc, "q": q, "f": f})
            matched_fires.add((f["lat"], f["lon"]))
    # Fire-only ≥50MW
    for f in fires:
        if f["frp"] < 50: continue
        if (f["lat"], f["lon"]) in matched_fires: continue
        sc = 35 if f["frp"] >= 100 else 30 if f["frp"] >= 75 else 25
        if f.get("confidence") == "h": sc += 5
        correlations.append({"type": "fire-only", "lat": f["lat"], "lon": f["lon"], "score": sc, "f": f})
    # Seismic-only (shallow munition-range)
    matched_quakes = set((c["q"]["lat"], c["q"]["lon"]) for c in correlations if "q" in c)
    for q in quakes:
        if (q["lat"], q["lon"]) in matched_quakes: continue
        if q["depth"] >= 5 or q["mag"] < 2.0 or q["mag"] > 5.0: continue
        sc = 20 + (10 if q["depth"] < 2 else 0)
        correlations.append({"type": "seismic-only", "lat": q["lat"], "lon": q["lon"], "score": sc, "q": q})
    # Dedup within 5km
    correlations.sort(key=lambda c: -c["score"])
    used = []
    deduped = []
    for c in correlations:
        if any(haversine(u["lat"], u["lon"], c["lat"], c["lon"]) < 5 for u in used): continue
        if c["score"] < SCORE_SUSPICIOUS: continue
        used.append(c)
        deduped.append(c)
    return deduped

# ═══════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════

def render(fires, quakes, correlations, sirens, output_path, caption_path=None):
    print(f"  🗺️ Building base map ({IMG_WIDTH}x{IMG_HEIGHT})...")
    
    # Calculate tile range
    tx1, ty1 = lat_lon_to_tile(MAP_NORTH, MAP_WEST, ZOOM)
    tx2, ty2 = lat_lon_to_tile(MAP_SOUTH, MAP_EAST, ZOOM)
    tile_w = tx2 - tx1 + 1
    tile_h = ty2 - ty1 + 1
    raw_w = tile_w * TILE_SIZE
    raw_h = tile_h * TILE_SIZE
    
    # Download tiles
    base = Image.new("RGBA", (raw_w, raw_h), (10, 10, 26, 255))
    for ty in range(ty1, ty2 + 1):
        for tx in range(tx1, tx2 + 1):
            tile = download_tile(ZOOM, tx, ty)
            base.paste(tile, ((tx - tx1) * TILE_SIZE, (ty - ty1) * TILE_SIZE))
    
    # Darken base for contrast
    dark = Image.new("RGBA", base.size, (0, 0, 10, 100))
    base = Image.alpha_composite(base, dark)
    
    # Scale to output size
    scale_x = IMG_WIDTH / raw_w
    scale_y = IMG_HEIGHT / raw_h
    base = base.resize((IMG_WIDTH, IMG_HEIGHT), Image.LANCZOS)
    
    draw = ImageDraw.Draw(base, "RGBA")
    
    def to_px(lat, lon):
        return lat_lon_to_pixel(lat, lon, ZOOM, tx1, ty1, scale_x, scale_y)
    
    def in_bounds(lat, lon):
        return MAP_SOUTH <= lat <= MAP_NORTH and MAP_WEST <= lon <= MAP_EAST
    
    now = time.time()
    
    # Draw known sites
    try:
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except:
        font_sm = ImageFont.load_default()
    
    for site in KNOWN_SITES:
        if not in_bounds(site["lat"], site["lon"]): continue
        px, py = to_px(site["lat"], site["lon"])
        draw.text((px + 6, py - 6), site["name"], fill=(200, 200, 220, 140), font=font_sm)
    
    # Draw fires (bottom layer)
    fire_count = 0
    for f in fires:
        if not in_bounds(f["lat"], f["lon"]): continue
        age_min = max(0, (now - f["ts"]) / 60) if f["ts"] else 9999
        if age_min > 360: continue
        px, py = to_px(f["lat"], f["lon"])
        if age_min < 60:
            color = COLOR_FIRE_HOT; r = 4
        elif age_min < 180:
            color = COLOR_FIRE_WARM; r = 3
        else:
            color = COLOR_FIRE_COOL; r = 2
        # Glow
        draw.ellipse([px-r*3, py-r*3, px+r*3, py+r*3], fill=(color[0], color[1], color[2], 40))
        draw.ellipse([px-r, py-r, px+r, py+r], fill=color)
        fire_count += 1
    
    # Draw seismic
    quake_count = 0
    for q in quakes:
        if not in_bounds(q["lat"], q["lon"]): continue
        px, py = to_px(q["lat"], q["lon"])
        r = max(4, int(q["mag"] * 3))
        c = COLOR_QUAKE_SHALLOW if q["depth"] < 5 else COLOR_QUAKE
        draw.ellipse([px-r, py-r, px+r, py+r], outline=c, width=2)
        draw.ellipse([px-2, py-2, px+2, py+2], fill=c)
        quake_count += 1
    
    # Draw correlations (top layer)
    probable = possible = suspicious = 0
    for c in correlations:
        if not in_bounds(c["lat"], c["lon"]): continue
        px, py = to_px(c["lat"], c["lon"])
        if c["score"] >= SCORE_PROBABLE:
            color = COLOR_STRIKE_PROBABLE; r = 18; w = 3; probable += 1
        elif c["score"] >= SCORE_POSSIBLE:
            color = COLOR_STRIKE_POSSIBLE; r = 14; w = 2; possible += 1
        else:
            color = COLOR_STRIKE_SUSPICIOUS; r = 10; w = 1; suspicious += 1
        # Ring
        draw.ellipse([px-r, py-r, px+r, py+r], outline=color, width=w)
        # Crosshair for probable
        if c["score"] >= SCORE_PROBABLE:
            draw.line([px-r-4, py, px+r+4, py], fill=color, width=1)
            draw.line([px, py-r-4, px, py+r+4], fill=color, width=1)
    
    # ═══════════════════════════════════════════════════════
    # HUD OVERLAY
    # ═══════════════════════════════════════════════════════
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except:
        font = font_lg = font_title = ImageFont.load_default()
    
    # Top bar
    draw.rectangle([0, 0, IMG_WIDTH, 44], fill=(10, 10, 26, 220))
    draw.text((14, 10), "CENTCOM THEATER OPS", fill=COLOR_HUD_RED, font=font_title)
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    draw.text((IMG_WIDTH - 200, 14), ts_str, fill=COLOR_HUD_DIM, font=font)
    draw.text((IMG_WIDTH - 200, 28), "MAGEN YEHUDA INTEL", fill=(255, 0, 64, 100), font=font_sm)
    
    # Stats panel (bottom-left)
    panel_y = IMG_HEIGHT - 110
    draw.rectangle([0, panel_y, 320, IMG_HEIGHT], fill=(10, 10, 26, 200))
    y = panel_y + 8
    stats = [
        (f"🔥 Fires: {fire_count}", COLOR_FIRE_HOT),
        (f"🔴 Seismic: {quake_count}", COLOR_QUAKE),
        (f"🎯 Probable: {probable}  ⚠️ Possible: {possible}  🔍 Suspicious: {suspicious}", COLOR_HUD_TEXT),
    ]
    if sirens:
        stats.insert(0, (f"🚨 Active Sirens: {len(sirens)}", COLOR_SIREN))
    for text, color in stats:
        draw.text((14, y), text, fill=color, font=font)
        y += 22
    
    # Legend (bottom-right)
    lx = IMG_WIDTH - 200
    draw.rectangle([lx - 10, panel_y, IMG_WIDTH, IMG_HEIGHT], fill=(10, 10, 26, 200))
    y = panel_y + 8
    legend = [
        ("● Fire (< 1h)", COLOR_FIRE_HOT),
        ("● Fire (1-3h)", COLOR_FIRE_WARM),
        ("○ Seismic", COLOR_QUAKE),
        ("◎ Probable Strike", COLOR_STRIKE_PROBABLE),
        ("○ Possible Strike", COLOR_STRIKE_POSSIBLE),
    ]
    for text, color in legend:
        draw.text((lx, y), text, fill=color, font=font_sm)
        y += 18
    
    # Save
    base = base.convert("RGB")
    base.save(output_path, "PNG", optimize=True)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅ Saved: {output_path} ({size_kb:.0f} KB)")
    
    # Generate caption
    lines = [
        "🎯 CENTCOM Theater Operations Snapshot",
        f"📅 {ts_str}",
        "",
    ]
    if sirens:
        lines.append(f"🚨 {len(sirens)} active siren alert(s)")
    if probable > 0:
        lines.append(f"🎯 {probable} PROBABLE strike correlation(s)")
    if possible > 0:
        lines.append(f"⚠️ {possible} possible strike correlation(s)")
    lines.append(f"🔥 {fire_count} satellite fire detections (≥{MIN_FIRE_FRP} MW)")
    lines.append(f"🔴 {quake_count} seismic events")
    if suspicious > 0:
        lines.append(f"🔍 {suspicious} suspicious anomalies")
    lines.extend([
        "",
        f"📡 Live dashboard: {DASHBOARD_URL}",
    ])
    caption = "\n".join(lines)
    print(f"\n{caption}")
    
    if caption_path:
        with open(caption_path, "w") as f:
            f.write(caption)
        print(f"  📝 Caption saved: {caption_path}")
    
    return caption

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/myi-dashboard-snapshot.png"
    caption_path = None
    if "--caption-file" in sys.argv:
        idx = sys.argv.index("--caption-file")
        caption_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "/tmp/myi-caption.txt"
    
    print("🎯 Magen Yehuda Intel — Dashboard Snapshot Generator")
    print("=" * 50)
    
    print("\n📡 Fetching live data from API...")
    fires = fetch_fires()
    print(f"  🔥 Fires: {len(fires)} (≥{MIN_FIRE_FRP} MW)")
    
    quakes = fetch_seismic()
    print(f"  🔴 Seismic: {len(quakes)}")
    
    sirens = fetch_sirens()
    print(f"  🚨 Sirens: {len(sirens)}")
    
    print("\n🧮 Computing strike correlations...")
    correlations = compute_correlations(fires, quakes)
    prob = sum(1 for c in correlations if c["score"] >= SCORE_PROBABLE)
    poss = sum(1 for c in correlations if SCORE_POSSIBLE <= c["score"] < SCORE_PROBABLE)
    susp = sum(1 for c in correlations if SCORE_SUSPICIOUS <= c["score"] < SCORE_POSSIBLE)
    print(f"  🎯 Probable: {prob}, ⚠️ Possible: {poss}, 🔍 Suspicious: {susp}")
    
    print(f"\n🗺️ Rendering map...")
    caption = render(fires, quakes, correlations, sirens, output_path, caption_path)
    
    print("\n✅ Done!")
    return caption

if __name__ == "__main__":
    main()
