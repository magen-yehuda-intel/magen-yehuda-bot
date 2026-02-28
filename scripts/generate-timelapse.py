#!/usr/bin/env python3
"""
Generate 24h time-lapse GIF of Iran fire/seismic activity.
Shows fire progression over the last 24 hours as an animated map
with country borders, known sites, and event markers.

Usage:
    python3 generate-timelapse.py <config.json> <state_dir> <output.gif> [--hours 24]
"""

import sys
import os
import json
import math
import io
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# ── Map config (matches generate-fire-map.py) ──
MAP_WEST = 43.5
MAP_EAST = 64.0
MAP_SOUTH = 24.5
MAP_NORTH = 40.5
TILE_SIZE = 256
ZOOM = 5

ESRI_SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
BORDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "borders.geojson")

KNOWN_SITES = [
    {"name": "Natanz", "lat": 33.72, "lon": 51.72, "type": "nuclear", "emoji": "☢️"},
    {"name": "Fordow", "lat": 34.88, "lon": 51.59, "type": "nuclear", "emoji": "☢️"},
    {"name": "Isfahan", "lat": 32.65, "lon": 51.68, "type": "nuclear", "emoji": "☢️"},
    {"name": "Bushehr", "lat": 28.83, "lon": 50.89, "type": "nuclear", "emoji": "☢️"},
    {"name": "Arak", "lat": 34.38, "lon": 49.24, "type": "nuclear", "emoji": "☢️"},
    {"name": "Tehran", "lat": 35.69, "lon": 51.39, "type": "capital", "emoji": "🏛️"},
    {"name": "Bandar Abbas", "lat": 27.19, "lon": 56.27, "type": "military", "emoji": "🎯"},
    {"name": "Kharg Island", "lat": 29.23, "lon": 50.31, "type": "oil", "emoji": "🛢️"},
    {"name": "Shiraz", "lat": 29.54, "lon": 52.59, "type": "military", "emoji": "🎯"},
    {"name": "Tabriz", "lat": 38.08, "lon": 46.29, "type": "military", "emoji": "🎯"},
    {"name": "Parchin", "lat": 35.52, "lon": 51.77, "type": "military", "emoji": "🎯"},
    {"name": "Shahrud", "lat": 36.42, "lon": 54.97, "type": "missile", "emoji": "🚀"},
]

FIRE_COLORS_BY_PRIORITY = {
    "critical": (255, 0, 0),
    "high": (255, 60, 0),
    "medium": (255, 165, 0),
    "low": (255, 255, 0),
}

SITE_COLORS = {
    "nuclear": (255, 0, 255),
    "capital": (255, 255, 0),
    "military": (0, 200, 255),
    "oil": (255, 140, 0),
    "missile": (255, 80, 80),
}


def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y


def lat_lon_to_pixel(lat, lon, zoom, ox, oy):
    n = 2 ** zoom
    px = (lon + 180) / 360 * n * TILE_SIZE - ox * TILE_SIZE
    lat_rad = math.radians(lat)
    py = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n * TILE_SIZE - oy * TILE_SIZE
    return int(px), int(py)


def download_tile(z, x, y):
    url = ESRI_SAT_URL.format(z=z, x=x, y=y)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IranIntelMap/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGBA")
    except:
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (30, 30, 30, 255))


def build_base_map(zoom):
    """Download satellite tiles and stitch them."""
    x_min, y_min = lat_lon_to_tile(MAP_NORTH, MAP_WEST, zoom)
    x_max, y_max = lat_lon_to_tile(MAP_SOUTH, MAP_EAST, zoom)
    width = (x_max - x_min + 1) * TILE_SIZE
    height = (y_max - y_min + 1) * TILE_SIZE
    img = Image.new("RGBA", (width, height))
    
    total = (x_max - x_min + 1) * (y_max - y_min + 1)
    count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tile = download_tile(zoom, x, y)
            img.paste(tile, ((x - x_min) * TILE_SIZE, (y - y_min) * TILE_SIZE))
            count += 1
    
    return img, x_min, y_min


def draw_borders(draw, zoom, ox, oy, img_w, img_h):
    """Draw country borders with Iran highlighted."""
    if not os.path.exists(BORDERS_FILE):
        print("  ⚠️ No borders file", file=sys.stderr)
        return
    
    with open(BORDERS_FILE) as f:
        geo = json.load(f)
    
    for feature in geo["features"]:
        name = feature["properties"].get("ADMIN", "")
        geom = feature["geometry"]
        is_iran = (name == "Iran")
        color = (255, 200, 50, 200) if is_iran else (180, 180, 180, 100)
        width = 3 if is_iran else 1
        
        polygons = []
        if geom["type"] == "Polygon":
            polygons = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            polygons = geom["coordinates"]
        
        for poly in polygons:
            ring = poly[0]
            points = []
            for coord in ring:
                lon, lat = coord[0], coord[1]
                if lon < MAP_WEST - 5 or lon > MAP_EAST + 5:
                    continue
                if lat < MAP_SOUTH - 5 or lat > MAP_NORTH + 5:
                    continue
                px, py = lat_lon_to_pixel(lat, lon, zoom, ox, oy)
                points.append((px, py))
            if len(points) >= 3:
                draw.line(points + [points[0]], fill=color, width=width)
                # Iran gold fill
                if is_iran:
                    try:
                        draw.polygon(points, fill=(255, 200, 50, 12))
                    except:
                        pass


def draw_known_sites(draw, zoom, ox, oy, font_sm):
    """Draw known military/nuclear sites as diamond markers with labels."""
    for site in KNOWN_SITES:
        px, py = lat_lon_to_pixel(site["lat"], site["lon"], zoom, ox, oy)
        color = SITE_COLORS.get(site["type"], (200, 200, 200))
        
        # Diamond shape
        s = 5
        diamond = [(px, py - s), (px + s, py), (px, py + s), (px - s, py)]
        draw.polygon(diamond, fill=(*color, 180), outline=(*color, 255))
        
        # Label
        draw.text((px + 8, py - 6), site["name"], fill=(*color, 200), font=font_sm)


def load_events(state_dir, hours=24):
    """Load fire/seismic events from state files."""
    cutoff = time.time() - (hours * 3600)
    
    fires = []
    try:
        with open(os.path.join(state_dir, "firms-seen.json")) as f:
            seen = json.load(f).get("seen", {})
        for key, data in seen.items():
            ts = data.get("ts", 0)
            if ts < cutoff:
                continue
            # Key format: "lat_lon_date"
            parts = key.split("_")
            try:
                lat = float(parts[0])
                lon = float(parts[1])
            except (ValueError, IndexError):
                continue
            if lat == 0 and lon == 0:
                continue
            fires.append({
                "lat": lat,
                "lon": lon,
                "frp": data.get("frp", 10),
                "ts": ts,
                "priority": data.get("priority", "medium"),
            })
    except Exception as e:
        print(f"  ⚠️ Loading fires: {e}", file=sys.stderr)
    
    quakes = []
    try:
        with open(os.path.join(state_dir, "seismic-seen.json")) as f:
            seen = json.load(f).get("seen", {})
        # Also try to get coords from intel log
        quake_coords = {}
        log_path = os.path.join(state_dir, "intel-log.jsonl")
        if os.path.exists(log_path):
            with open(log_path) as f:
                for line in f:
                    try:
                        ev = json.loads(line.strip())
                        if ev.get("type") == "seismic":
                            d = ev.get("data", {})
                            if isinstance(d, str):
                                d = json.loads(d)
                            if isinstance(d, dict):
                                for q in d.get("quakes", [d]):
                                    qid = q.get("id", "")
                                    if qid and q.get("lat"):
                                        quake_coords[qid] = {"lat": q["lat"], "lon": q["lon"]}
                    except:
                        continue
        
        for key, data in seen.items():
            ts = data.get("ts", 0)
            if ts < cutoff:
                continue
            lat = data.get("lat", 0)
            lon = data.get("lon", 0)
            # Try intel log coords
            if (lat == 0 or lon == 0) and key in quake_coords:
                lat = quake_coords[key]["lat"]
                lon = quake_coords[key]["lon"]
            # Try USGS API as fallback
            if lat == 0 or lon == 0:
                try:
                    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={key}&format=geojson"
                    req = urllib.request.Request(url, headers={"User-Agent": "MagenYehudaBot/1.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        qdata = json.loads(resp.read())
                        coords = qdata["geometry"]["coordinates"]
                        lon, lat = coords[0], coords[1]
                except:
                    pass
            if lat != 0 and lon != 0:
                quakes.append({
                    "lat": lat,
                    "lon": lon,
                    "mag": data.get("mag", 3),
                    "ts": ts,
                    "priority": data.get("priority", "medium"),
                })
    except Exception as e:
        print(f"  ⚠️ Loading quakes: {e}", file=sys.stderr)
    
    return fires, quakes


def get_fonts():
    """Load fonts with fallbacks."""
    try:
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_md = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except:
        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font_lg = ImageFont.load_default()
            font_md = font_lg
            font_sm = font_lg
    return font_lg, font_md, font_sm


def generate_frame(base_img, fires, quakes, frame_time, zoom, ox, oy,
                   frame_num, total_frames, hours, font_lg, font_md, font_sm,
                   total_fires, total_quakes):
    """Generate a single animation frame."""
    frame = base_img.copy()
    draw = ImageDraw.Draw(frame, "RGBA")
    w, h = frame.size
    
    # ── Draw events up to this frame's time ──
    active_fires = [f for f in fires if f["ts"] <= frame_time]
    active_quakes = [q for q in quakes if q["ts"] <= frame_time]
    
    # Fires: glow + dot, older = more transparent
    for fire in active_fires:
        age = frame_time - fire["ts"]
        fade = max(0.4, 1.0 - (age / (hours * 3600)) * 0.6)
        
        px, py = lat_lon_to_pixel(fire["lat"], fire["lon"], zoom, ox, oy)
        if px < 0 or py < 0 or px > w or py > h:
            continue
        
        priority = fire.get("priority", "medium")
        base_color = FIRE_COLORS_BY_PRIORITY.get(priority, (255, 165, 0))
        frp = fire.get("frp", 10)
        dot_size = max(4, min(int(4 + frp / 15), 14))
        
        alpha = int(220 * fade)
        glow_alpha = int(60 * fade)
        
        # Outer glow
        gs = dot_size + 8
        draw.ellipse([px - gs, py - gs, px + gs, py + gs],
                     fill=(*base_color, glow_alpha))
        # Inner glow
        gs2 = dot_size + 4
        draw.ellipse([px - gs2, py - gs2, px + gs2, py + gs2],
                     fill=(*base_color, int(glow_alpha * 1.5)))
        # Core dot
        draw.ellipse([px - dot_size, py - dot_size, px + dot_size, py + dot_size],
                     fill=(*base_color, alpha))
        # Bright center
        cs = max(2, dot_size // 2)
        draw.ellipse([px - cs, py - cs, px + cs, py + cs],
                     fill=(255, 255, 255, int(alpha * 0.7)))
    
    # Quakes: pulsing ring
    for quake in active_quakes:
        age = frame_time - quake["ts"]
        fade = max(0.4, 1.0 - (age / (hours * 3600)) * 0.6)
        
        px, py = lat_lon_to_pixel(quake["lat"], quake["lon"], zoom, ox, oy)
        if px < 0 or py < 0 or px > w or py > h:
            continue
        
        mag = quake.get("mag", 3)
        base_size = int(6 + (mag - 2.5) * 5)
        alpha = int(200 * fade)
        
        # Pulse effect
        pulse = 1.0 + 0.3 * math.sin(frame_num * 0.5)
        ring_size = int(base_size * pulse) + 10
        
        # Outer ring
        draw.ellipse([px - ring_size, py - ring_size, px + ring_size, py + ring_size],
                     outline=(180, 0, 255, int(alpha * 0.4)), width=2)
        # Inner ring
        ring2 = int(base_size * pulse) + 4
        draw.ellipse([px - ring2, py - ring2, px + ring2, py + ring2],
                     outline=(180, 0, 255, int(alpha * 0.7)), width=2)
        # Core
        draw.ellipse([px - base_size, py - base_size, px + base_size, py + base_size],
                     fill=(180, 0, 255, alpha))
        # Magnitude label
        draw.text((px + base_size + 4, py - 6), f"M{mag:.1f}",
                  fill=(220, 180, 255, alpha), font=font_sm)
    
    # ── Title bar (top) ──
    draw.rectangle([0, 0, w, 42], fill=(0, 0, 0, 210))
    time_str = datetime.fromtimestamp(frame_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    draw.text((12, 6), f"IRAN INTEL — {hours}h TIME-LAPSE", fill=(255, 200, 50, 255), font=font_lg)
    draw.text((12, 25), time_str, fill=(180, 180, 180, 230), font=font_sm)
    
    # ── Progress bar ──
    progress = frame_num / max(total_frames - 1, 1)
    bar_y = 40
    bar_w = w - 20
    draw.rectangle([10, bar_y, 10 + bar_w, bar_y + 2], fill=(60, 60, 60, 150))
    draw.rectangle([10, bar_y, 10 + int(bar_w * progress), bar_y + 2], fill=(255, 200, 50, 220))
    
    # ── Stats panel (bottom left) ──
    panel_h = 52
    draw.rectangle([0, h - panel_h, 220, h], fill=(0, 0, 0, 190))
    draw.text((10, h - panel_h + 6),
              f"🔥 {len(active_fires)}/{total_fires} fires",
              fill=(255, 160, 50, 240), font=font_md)
    draw.text((10, h - panel_h + 26),
              f"🌍 {len(active_quakes)}/{total_quakes} earthquakes",
              fill=(180, 120, 255, 240), font=font_md)
    
    # ── Legend (bottom right) ──
    legend_w = 160
    legend_h = 75
    lx = w - legend_w - 5
    ly = h - legend_h - 5
    draw.rounded_rectangle([lx, ly, lx + legend_w, ly + legend_h], radius=6, fill=(0, 0, 0, 180))
    draw.text((lx + 8, ly + 4), "Legend", fill=(255, 255, 255, 200), font=font_sm)
    
    # Fire dots
    cy = ly + 18
    for label, color in [("Critical fire", (255, 0, 0)), ("High fire", (255, 60, 0)),
                          ("Medium fire", (255, 165, 0)), ("Earthquake", (180, 0, 255))]:
        draw.ellipse([lx + 10, cy, lx + 18, cy + 8], fill=(*color, 220))
        draw.text((lx + 24, cy - 2), label, fill=(200, 200, 200, 200), font=font_sm)
        cy += 13
    
    # ── Known site diamond in legend ──
    dy = cy
    dx = lx + 14
    draw.polygon([(dx, dy), (dx + 4, dy + 4), (dx, dy + 8), (dx - 4, dy + 4)],
                 fill=(255, 0, 255, 200))
    draw.text((lx + 24, dy), "Known site", fill=(200, 200, 200, 200), font=font_sm)
    
    # ── Branding ──
    draw.text((w - 180, 6), "Magen Yehuda Intel",
              fill=(255, 200, 50, 150), font=font_sm)
    
    return frame.convert("RGB")


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 generate-timelapse.py <config.json> <state_dir> <output.gif> [--hours 24]", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    state_dir = sys.argv[2]
    output_path = sys.argv[3]
    
    hours = 24
    for i, arg in enumerate(sys.argv):
        if arg == "--hours" and i + 1 < len(sys.argv):
            hours = int(sys.argv[i + 1])
    
    print(f"  Generating {hours}h time-lapse...", file=sys.stderr)
    
    # Load events
    fires, quakes = load_events(state_dir, hours)
    print(f"  Events: {len(fires)} fires, {len(quakes)} quakes", file=sys.stderr)
    
    if not fires and not quakes:
        print("  No events to animate — skipping", file=sys.stderr)
        sys.exit(0)
    
    # Build base map
    print("  Downloading satellite tiles...", file=sys.stderr)
    base_map, ox, oy = build_base_map(ZOOM)
    
    # Draw static layers on base
    print("  Drawing borders + known sites...", file=sys.stderr)
    draw = ImageDraw.Draw(base_map, "RGBA")
    font_lg, font_md, font_sm = get_fonts()
    draw_borders(draw, ZOOM, ox, oy, base_map.width, base_map.height)
    draw_known_sites(draw, ZOOM, ox, oy, font_sm)
    
    # Generate frames
    now = time.time()
    start_time = now - (hours * 3600)
    
    # All events happened in a narrow window — spread frames to show progression
    all_ts = sorted([f["ts"] for f in fires] + [q["ts"] for q in quakes])
    earliest = min(all_ts) if all_ts else start_time
    latest = max(all_ts) if all_ts else now
    
    # 36 frames: 3 before first event, 30 progression, 3 hold at end
    num_frames = 36
    lead_frames = 3
    hold_frames = 5
    progress_frames = num_frames - lead_frames - hold_frames
    
    frames = []
    print(f"  Rendering {num_frames} frames...", file=sys.stderr)
    
    for i in range(num_frames):
        if i < lead_frames:
            # Before first event — show empty map
            frame_time = earliest - (hours * 3600 * 0.01)
        elif i >= num_frames - hold_frames:
            # Hold on final frame
            frame_time = latest + 1
        else:
            # Progress through events
            p = (i - lead_frames) / max(progress_frames - 1, 1)
            frame_time = earliest + p * (latest - earliest + 60)
        
        frame = generate_frame(
            base_map, fires, quakes, frame_time, ZOOM, ox, oy,
            i, num_frames, hours, font_lg, font_md, font_sm,
            len(fires), len(quakes)
        )
        frames.append(frame)
        
        if (i + 1) % 10 == 0:
            print(f"  Frame {i + 1}/{num_frames}", file=sys.stderr)
    
    # Save GIF
    print(f"  Encoding GIF...", file=sys.stderr)
    
    # Duration per frame: faster during progression, slower at start/end
    durations = []
    for i in range(len(frames)):
        if i < lead_frames:
            durations.append(800)   # Pause on empty map
        elif i >= len(frames) - hold_frames:
            durations.append(1200)  # Hold on final
        else:
            durations.append(250)   # Quick progression
    
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    
    size = os.path.getsize(output_path)
    print(f"  ✅ GIF: {output_path} ({size // 1024}KB, {len(frames)} frames)", file=sys.stderr)
    print(output_path)


if __name__ == "__main__":
    main()
