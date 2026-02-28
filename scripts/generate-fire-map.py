#!/usr/bin/env python3
"""
Generate an Iran intel map showing satellite fire hotspots AND seismic activity.
Downloads ESRI satellite tiles and overlays fire dots + earthquake markers.
Outputs a PNG image.

Usage:
    python3 generate-fire-map.py <fires.json> <output.png> [--seismic <seismic.json>]
    
    fires.json: Output from scan-fires.py
    seismic.json: Output from scan-seismic.py (optional)
    output.png: Path to write the map image
"""

import sys
import os
import json
import math
import io
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# Iran map bounds
MAP_WEST = 43.5
MAP_EAST = 64.0
MAP_SOUTH = 24.5
MAP_NORTH = 40.5

# Border GeoJSON path (relative to script)
BORDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "borders.geojson")

ESRI_SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILE_SIZE = 256
ZOOM = 5

# Fire priority colors (RGBA)
FIRE_COLORS = {
    "critical": (255, 0, 0, 230),
    "high": (255, 60, 0, 210),
    "medium": (255, 165, 0, 190),
    "low": (255, 255, 0, 160),
}
FIRE_GLOW = {
    "critical": (255, 0, 0, 100),
    "high": (255, 60, 0, 80),
    "medium": (255, 165, 0, 60),
    "low": (255, 255, 0, 40),
}

# Seismic magnitude colors (concentric ring style)
QUAKE_COLORS = {
    "critical": (220, 0, 255, 230),     # Purple (explosion/suspicious)
    "high": (0, 150, 255, 210),          # Blue
    "medium": (0, 200, 255, 180),        # Light blue
    "low": (100, 220, 255, 140),         # Cyan
}
QUAKE_RING = {
    "critical": (255, 0, 255, 150),
    "high": (0, 120, 255, 120),
    "medium": (0, 180, 255, 90),
    "low": (100, 200, 255, 70),
}

KNOWN_SITES = [
    {"name": "Natanz", "lat": 33.72, "lon": 51.72, "type": "nuclear"},
    {"name": "Fordow", "lat": 34.88, "lon": 51.59, "type": "nuclear"},
    {"name": "Isfahan", "lat": 32.65, "lon": 51.68, "type": "nuclear"},
    {"name": "Bushehr", "lat": 28.83, "lon": 50.89, "type": "nuclear"},
    {"name": "Arak", "lat": 34.38, "lon": 49.24, "type": "nuclear"},
    {"name": "Tehran", "lat": 35.69, "lon": 51.39, "type": "capital"},
    {"name": "Bandar Abbas", "lat": 27.19, "lon": 56.27, "type": "military"},
    {"name": "Kharg Island", "lat": 29.23, "lon": 50.31, "type": "oil"},
    {"name": "Shiraz", "lat": 29.54, "lon": 52.59, "type": "military"},
    {"name": "Tabriz", "lat": 38.08, "lon": 46.29, "type": "military"},
]


def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y


def lat_lon_to_pixel(lat, lon, zoom, origin_x, origin_y):
    n = 2 ** zoom
    px = (lon + 180) / 360 * n * TILE_SIZE - origin_x * TILE_SIZE
    lat_rad = math.radians(lat)
    py = (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n * TILE_SIZE - origin_y * TILE_SIZE
    return int(px), int(py)


def download_tile(z, x, y):
    url = ESRI_SAT_URL.format(z=z, x=x, y=y)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IranIntelMap/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGBA")
    except Exception:
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (30, 30, 30, 255))


def build_base_map(zoom, west, south, east, north):
    x_min, y_min = lat_lon_to_tile(north, west, zoom)
    x_max, y_max = lat_lon_to_tile(south, east, zoom)
    width = (x_max - x_min + 1) * TILE_SIZE
    height = (y_max - y_min + 1) * TILE_SIZE
    img = Image.new("RGBA", (width, height))
    count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tile = download_tile(zoom, x, y)
            img.paste(tile, ((x - x_min) * TILE_SIZE, (y - y_min) * TILE_SIZE))
            count += 1
    print(f"  Downloaded {count} tiles ({width}x{height}px)", file=sys.stderr)
    return img, x_min, y_min


def draw_fire_dots(img, fires, zoom, ox, oy):
    draw = ImageDraw.Draw(img, "RGBA")
    priority_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    fires_sorted = sorted(fires, key=lambda f: priority_order.get(f.get("priority", "low"), 0))

    for fire in fires_sorted:
        px, py = lat_lon_to_pixel(fire["lat"], fire["lon"], zoom, ox, oy)
        priority = fire.get("priority", "medium")
        frp = fire.get("frp", 10)

        base_size = 6
        if frp >= 100: base_size = 16
        elif frp >= 50: base_size = 12
        elif frp >= 20: base_size = 9
        elif frp >= 10: base_size = 7

        # Glow
        glow = FIRE_GLOW.get(priority, (255, 165, 0, 60))
        gs = base_size + 8
        draw.ellipse([px-gs, py-gs, px+gs, py+gs], fill=glow)
        # Dot
        color = FIRE_COLORS.get(priority, (255, 165, 0, 200))
        draw.ellipse([px-base_size, py-base_size, px+base_size, py+base_size], fill=color)
        # White center for critical/high
        if priority in ("critical", "high"):
            cs = max(2, base_size // 3)
            draw.ellipse([px-cs, py-cs, px+cs, py+cs], fill=(255, 255, 255, 200))
    return img


def draw_quake_markers(img, quakes, zoom, ox, oy):
    """Draw earthquake markers as concentric rings with magnitude labels."""
    draw = ImageDraw.Draw(img, "RGBA")

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
        font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
        except Exception:
            font = ImageFont.load_default()
            font_big = font

    priority_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    quakes_sorted = sorted(quakes, key=lambda q: priority_order.get(q.get("priority", "low"), 0))

    for quake in quakes_sorted:
        px, py = lat_lon_to_pixel(quake["lat"], quake["lon"], zoom, ox, oy)
        priority = quake.get("priority", "medium")
        mag = quake.get("mag", 3)
        suspicious = quake.get("suspicious", False)

        # Size based on magnitude
        base_size = int(6 + (mag - 2.5) * 5)
        base_size = max(6, min(base_size, 30))

        # Outer seismic ring (pulsing circle look)
        ring_color = QUAKE_RING.get(priority, (0, 180, 255, 90))
        ring_size = base_size + 12
        draw.ellipse([px-ring_size, py-ring_size, px+ring_size, py+ring_size],
                      outline=ring_color, width=2)
        # Second ring
        ring2 = base_size + 7
        draw.ellipse([px-ring2, py-ring2, px+ring2, py+ring2],
                      outline=(*ring_color[:3], ring_color[3] + 40), width=2)

        # Main circle
        color = QUAKE_COLORS.get(priority, (0, 200, 255, 180))
        draw.ellipse([px-base_size, py-base_size, px+base_size, py+base_size], fill=color)

        # Inner ring
        inner = base_size - 3
        if inner > 2:
            draw.ellipse([px-inner, py-inner, px+inner, py+inner],
                          outline=(255, 255, 255, 150), width=1)

        # Suspicious marker (⚠ triangle overlay)
        if suspicious:
            tri_size = base_size + 4
            draw.polygon([
                (px, py - tri_size),
                (px - tri_size, py + tri_size // 2),
                (px + tri_size, py + tri_size // 2),
            ], outline=(255, 0, 255, 200), width=2)

        # Magnitude label
        mag_str = f"M{mag:.1f}"
        f = font_big if mag >= 4.5 else font
        draw.text((px + base_size + 5, py - 7), mag_str,
                   fill=(255, 255, 255, 230), font=f,
                   stroke_width=2, stroke_fill=(0, 0, 0, 200))

        # Depth label
        depth = quake.get("depth_km", 0)
        draw.text((px + base_size + 5, py + 7), f"{depth:.0f}km",
                   fill=(180, 220, 255, 200), font=font,
                   stroke_width=1, stroke_fill=(0, 0, 0, 150))

    return img


def draw_borders(img, zoom, ox, oy):
    """Draw country borders from GeoJSON. Iran border highlighted."""
    if not os.path.exists(BORDERS_FILE):
        print(f"  ⚠️  Borders file not found: {BORDERS_FILE}", file=sys.stderr)
        return img

    with open(BORDERS_FILE) as f:
        geo = json.load(f)

    draw = ImageDraw.Draw(img, "RGBA")

    # Load font for country labels
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except Exception:
        try:
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except Exception:
            label_font = ImageFont.load_default()

    # Country label positions (lon, lat) — hand-tuned for readability
    COUNTRY_LABELS = {
        "Iran": (54.5, 33.0),
        "Iraq": (44.5, 33.5),
        "Turkey": (46.0, 39.5),
        "Afghanistan": (63.0, 34.0),
        "Pakistan": (63.0, 28.0),
        "Turkmenistan": (58.0, 39.5),
        "Saudi Arabia": (47.0, 26.0),
        "Kuwait": (47.7, 29.6),
        "Qatar": (51.2, 25.5),
        "UAE": (54.5, 24.8),
        "Oman": (57.5, 24.8),
        "Azerbaijan": (48.5, 40.0),
        "Armenia": (44.5, 40.2),
        "Syria": (43.8, 35.5),
        "Jordan": (44.0, 31.5),
        "Georgia": (44.0, 41.5),
    }

    def geojson_ring_to_pixels(ring):
        """Convert a GeoJSON coordinate ring to pixel coordinates."""
        points = []
        for coord in ring:
            lon, lat = coord[0], coord[1]
            # Skip points way outside our view
            if lon < MAP_WEST - 5 or lon > MAP_EAST + 5 or lat < MAP_SOUTH - 5 or lat > MAP_NORTH + 5:
                continue
            px, py = lat_lon_to_pixel(lat, lon, zoom, ox, oy)
            points.append((px, py))
        return points

    # First pass: draw all borders as thin lines
    for feature in geo["features"]:
        name = feature["properties"].get("ADMIN", "")
        geom = feature["geometry"]

        is_iran = (name == "Iran")
        # Iran: bright border, others: subtle
        border_color = (255, 200, 50, 200) if is_iran else (200, 200, 200, 100)
        border_width = 3 if is_iran else 1

        polygons = []
        if geom["type"] == "Polygon":
            polygons = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            polygons = geom["coordinates"]

        for poly in polygons:
            # Outer ring only (index 0), skip holes
            ring = poly[0]
            points = geojson_ring_to_pixels(ring)
            if len(points) < 3:
                continue
            # Draw border line
            draw.line(points + [points[0]], fill=border_color, width=border_width)

    # Second pass: draw Iran fill (very subtle tint)
    for feature in geo["features"]:
        name = feature["properties"].get("ADMIN", "")
        if name != "Iran":
            continue
        geom = feature["geometry"]
        polygons = []
        if geom["type"] == "Polygon":
            polygons = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            polygons = geom["coordinates"]
        for poly in polygons:
            points = geojson_ring_to_pixels(poly[0])
            if len(points) >= 3:
                draw.polygon(points, fill=(255, 200, 50, 20))  # Very subtle gold tint

    # Country labels
    for name, (lon, lat) in COUNTRY_LABELS.items():
        if MAP_WEST <= lon <= MAP_EAST and MAP_SOUTH <= lat <= MAP_NORTH:
            px, py = lat_lon_to_pixel(lat, lon, zoom, ox, oy)
            if name == "Iran":
                draw.text((px, py), name.upper(), fill=(255, 220, 100, 180), font=label_font,
                           stroke_width=2, stroke_fill=(0, 0, 0, 160), anchor="mm")
            else:
                draw.text((px, py), name, fill=(200, 200, 200, 130), font=label_font,
                           stroke_width=1, stroke_fill=(0, 0, 0, 120), anchor="mm")

    return img


def draw_known_sites(img, zoom, ox, oy):
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font = ImageFont.load_default()

    for site in KNOWN_SITES:
        px, py = lat_lon_to_pixel(site["lat"], site["lon"], zoom, ox, oy)
        size = 4
        diamond = [(px, py-size), (px+size, py), (px, py+size), (px-size, py)]

        if site["type"] == "nuclear": color = (0, 255, 255, 180)
        elif site["type"] == "capital": color = (255, 255, 255, 180)
        elif site["type"] == "oil": color = (200, 100, 255, 180)
        else: color = (100, 200, 255, 150)

        draw.polygon(diamond, fill=color, outline=(255, 255, 255, 120))
        draw.text((px+7, py-6), site["name"], fill=(255, 255, 255, 200), font=font,
                   stroke_width=1, stroke_fill=(0, 0, 0, 180))
    return img


def draw_legend(img, has_fires, has_quakes, fire_count=0, quake_count=0):
    draw = ImageDraw.Draw(img, "RGBA")

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
            font_title = font

    w, h = img.size
    # Calculate legend height
    rows = 1  # Known Sites
    if has_fires: rows += 5  # title + 4 levels
    if has_quakes: rows += 3  # title + mag scale + suspicious
    box_h = 30 + rows * 20
    box_w = 190
    box_x, box_y = 10, h - box_h - 10

    draw.rounded_rectangle([box_x, box_y, box_x+box_w, box_y+box_h],
                            radius=8, fill=(0, 0, 0, 190))

    y = box_y + 8

    # Fire legend
    if has_fires:
        draw.text((box_x+10, y), f"🔥 Fires ({fire_count})", fill=(255, 200, 100, 240), font=font_title)
        y += 22
        for label, color in [("CRITICAL", (255,0,0,230)), ("HIGH", (255,60,0,210)),
                               ("MEDIUM", (255,165,0,190)), ("LOW", (255,255,0,160))]:
            draw.ellipse([box_x+15, y+1, box_x+25, y+11], fill=color)
            draw.text((box_x+30, y-1), label, fill=(255,255,255,220), font=font)
            y += 18

    # Quake legend
    if has_quakes:
        y += 4
        draw.text((box_x+10, y), f"🌍 Quakes ({quake_count})", fill=(100, 200, 255, 240), font=font_title)
        y += 22
        # Concentric ring sample
        cx, cy = box_x + 20, y + 5
        draw.ellipse([cx-8, cy-8, cx+8, cy+8], fill=(0, 180, 255, 160))
        draw.ellipse([cx-12, cy-12, cx+12, cy+12], outline=(0, 150, 255, 120), width=1)
        draw.text((box_x+38, y-1), "Earthquake", fill=(180, 220, 255, 220), font=font)
        y += 20
        # Suspicious
        draw.polygon([(box_x+20, y), (box_x+14, y+10), (box_x+26, y+10)],
                      outline=(255, 0, 255, 200), width=2)
        draw.text((box_x+38, y-1), "Suspicious", fill=(255, 150, 255, 220), font=font)
        y += 20

    # Known sites
    y += 2
    draw.polygon([(box_x+20, y), (box_x+25, y+5), (box_x+20, y+10), (box_x+15, y+5)],
                  fill=(0, 255, 255, 180))
    draw.text((box_x+30, y-1), "Known Sites", fill=(200, 200, 200, 200), font=font)

    # Title bar
    title_parts = []
    if has_fires: title_parts.append("🔥 Fires")
    if has_quakes: title_parts.append("🌍 Seismic")
    title = " + ".join(title_parts) if title_parts else "Intel"
    draw.rounded_rectangle([0, 0, w, 35], radius=0, fill=(0, 0, 0, 190))
    draw.text((10, 7), f"🛰️ Iran {title} — Satellite Detection",
              fill=(255, 255, 255, 240), font=font_title)

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    draw.text((w - 175, 9), ts, fill=(180, 180, 180, 200), font=font)

    return img


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate-fire-map.py <fires.json> <output.png> [--seismic <seismic.json>]", file=sys.stderr)
        sys.exit(1)

    fires_path = sys.argv[1]
    output_path = sys.argv[2]

    # Parse --seismic flag
    seismic_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--seismic" and i + 1 < len(sys.argv):
            seismic_path = sys.argv[i + 1]

    # Load fire data
    with open(fires_path) as f:
        fire_data = json.load(f)
    fires = fire_data.get("fires", [])

    # Load seismic data
    quakes = []
    if seismic_path and os.path.exists(seismic_path):
        with open(seismic_path) as f:
            seismic_data = json.load(f)
        quakes = seismic_data.get("quakes", [])

    has_fires = len(fires) > 0
    has_quakes = len(quakes) > 0

    if not has_fires and not has_quakes:
        print("No fires or quakes to plot", file=sys.stderr)

    total = len(fires) + len(quakes)
    print(f"  Generating map: {len(fires)} fires + {len(quakes)} quakes...", file=sys.stderr)

    # Build base map
    base_map, ox, oy = build_base_map(ZOOM, MAP_WEST, MAP_SOUTH, MAP_EAST, MAP_NORTH)

    # Layer order: borders (bottom) → sites → fires → quakes (top)
    base_map = draw_borders(base_map, ZOOM, ox, oy)
    base_map = draw_known_sites(base_map, ZOOM, ox, oy)
    if has_fires:
        base_map = draw_fire_dots(base_map, fires, ZOOM, ox, oy)
    if has_quakes:
        base_map = draw_quake_markers(base_map, quakes, ZOOM, ox, oy)

    # Legend
    base_map = draw_legend(base_map, has_fires, has_quakes, len(fires), len(quakes))

    # Save
    output = base_map.convert("RGB")
    output.save(output_path, "PNG", optimize=True)

    file_size = os.path.getsize(output_path)
    print(f"  ✅ Map saved: {output_path} ({file_size // 1024}KB, {output.size[0]}x{output.size[1]})", file=sys.stderr)
    print(output_path)


if __name__ == "__main__":
    main()
