#!/usr/bin/env python3
"""
generate-strikes-map.py — Generate a visual strikes map from strikes-data.json

Renders a dark-themed map of the Middle East with strike markers:
  - Color-coded by actor side (Israel=blue, Iran=red, US=navy, proxy=orange, etc.)
  - Size scaled by fatalities
  - Shape by event type (circle=airstrike, diamond=missile, triangle=ground)
  - Confidence opacity (high=solid, medium=semi, low=faint)
  - Legend with actor counts and date range
  - Optional heatmap layer for density

Usage:
    python3 generate-strikes-map.py <config.json> <state_dir> [--output path.png]

Config fields (in config.json → strikes):
    map_width: 1600              # Pixels
    map_height: 1000             # Pixels
    map_style: "dark"            # "dark" or "light"
    show_heatmap: true           # Density heatmap layer
    show_legend: true            # Actor legend
    show_timeline: true          # Date bar at bottom
    max_markers: 5000            # Limit markers for performance
    highlight_recent_hours: 48   # Highlight events from last N hours
"""

import json
import os
import sys
import math
from datetime import datetime, timezone, timedelta

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("  [strikes-map] WARNING: Pillow not installed, map generation disabled", file=sys.stderr)

# ═══════════════════════════════════════════════════════════
# MAP CONFIGURATION
# ═══════════════════════════════════════════════════════════

MAP_DEFAULTS = {
    "map_width": 1600,
    "map_height": 1000,
    "map_style": "dark",
    "show_heatmap": False,
    "show_legend": True,
    "show_timeline": True,
    "max_markers": 5000,
    "highlight_recent_hours": 48,
}

# Map bounds — Middle East region
# lat: 10°N to 42°N, lon: 28°E to 65°E
MAP_BOUNDS = {
    "lat_min": 10.0,
    "lat_max": 42.0,
    "lon_min": 28.0,
    "lon_max": 65.0,
}

# Color schemes
SIDE_COLORS = {
    "israel":     (0, 120, 255),     # Blue
    "iran":       (220, 30, 30),     # Red
    "iran_proxy": (255, 140, 0),     # Orange
    "us":         (0, 50, 150),      # Navy
    "syria":      (100, 100, 100),   # Gray
    "gulf":       (0, 180, 100),     # Green
    "unknown":    (180, 180, 180),   # Light gray
}

SIDE_LABELS = {
    "israel": "Israel (IDF)",
    "iran": "Iran (IRGC/Military)",
    "iran_proxy": "Iran Proxies (Hezbollah/Hamas/Houthis)",
    "us": "United States (CENTCOM)",
    "syria": "Syria (SAA)",
    "gulf": "Gulf States",
    "unknown": "Unknown/Other",
}

# Dark map background colors
DARK_BG = (18, 18, 28)
DARK_WATER = (15, 25, 50)
DARK_LAND = (30, 35, 45)
DARK_BORDER = (50, 55, 65)
DARK_TEXT = (200, 200, 210)
DARK_GRID = (35, 40, 55)

# Simplified country polygons (bounding boxes for land coloring)
# These are rough approximations for visual effect
COUNTRY_BOUNDS = {
    "Iran": {"lat": (25, 40), "lon": (44, 63)},
    "Iraq": {"lat": (29, 37.5), "lon": (38.8, 48.5)},
    "Syria": {"lat": (32, 37.3), "lon": (35.7, 42.4)},
    "Lebanon": {"lat": (33.0, 34.7), "lon": (35.1, 36.6)},
    "Israel": {"lat": (29.5, 33.3), "lon": (34.2, 35.9)},
    "Jordan": {"lat": (29.2, 33.4), "lon": (34.9, 39.3)},
    "Saudi Arabia": {"lat": (16, 32.2), "lon": (34.5, 55.7)},
    "Yemen": {"lat": (12.1, 19), "lon": (42.5, 54.5)},
    "Turkey": {"lat": (36, 42), "lon": (28, 44.8)},
    "Egypt": {"lat": (22, 31.7), "lon": (24.7, 36.9)},
    "UAE": {"lat": (22.6, 26.1), "lon": (51, 56.4)},
    "Oman": {"lat": (16.6, 26.4), "lon": (52, 59.8)},
    "Kuwait": {"lat": (28.5, 30.1), "lon": (46.5, 48.4)},
    "Bahrain": {"lat": (25.8, 26.3), "lon": (50.3, 50.7)},
    "Qatar": {"lat": (24.5, 26.2), "lon": (50.7, 51.7)},
    "Palestine": {"lat": (31.2, 32.6), "lon": (34.2, 35.6)},
}


def latlon_to_pixel(lat, lon, width, height, bounds=MAP_BOUNDS):
    """Convert lat/lon to pixel coordinates using Mercator-ish projection."""
    # Simple equirectangular projection (good enough for regional maps)
    x = (lon - bounds["lon_min"]) / (bounds["lon_max"] - bounds["lon_min"]) * width
    y = (bounds["lat_max"] - lat) / (bounds["lat_max"] - bounds["lat_min"]) * height
    return int(x), int(y)


def draw_map_background(draw, width, height):
    """Draw dark map background with country outlines."""
    # Fill with water color
    draw.rectangle([0, 0, width, height], fill=DARK_WATER)

    # Draw land masses (rough bounding boxes)
    for country, bounds in COUNTRY_BOUNDS.items():
        x1, y1 = latlon_to_pixel(bounds["lat"][1], bounds["lon"][0], width, height)
        x2, y2 = latlon_to_pixel(bounds["lat"][0], bounds["lon"][1], width, height)
        draw.rectangle([x1, y1, x2, y2], fill=DARK_LAND, outline=DARK_BORDER)

    # Grid lines
    for lat in range(12, 42, 5):
        _, y = latlon_to_pixel(lat, 28, width, height)
        draw.line([(0, y), (width, y)], fill=DARK_GRID, width=1)
        draw.text((5, y + 2), f"{lat}°N", fill=(60, 65, 80))

    for lon in range(30, 65, 5):
        x, _ = latlon_to_pixel(42, lon, width, height)
        draw.line([(x, 0), (x, height)], fill=DARK_GRID, width=1)
        draw.text((x + 2, height - 15), f"{lon}°E", fill=(60, 65, 80))


def get_marker_size(fatalities, base=4):
    """Scale marker size by fatalities."""
    if fatalities <= 0:
        return base
    return min(base + int(math.sqrt(fatalities) * 1.5), 25)


def draw_strike_marker(draw, x, y, size, color, confidence, sub_event="", recent=False):
    """Draw a strike marker with optional styling."""
    # Adjust opacity based on confidence
    alpha_map = {"high": 255, "medium": 180, "low": 100}
    alpha = alpha_map.get(confidence, 180)

    # Adjust color with alpha simulation (blend with background)
    r, g, b = color
    bg_r, bg_g, bg_b = DARK_WATER
    factor = alpha / 255
    blended = (
        int(r * factor + bg_r * (1 - factor)),
        int(g * factor + bg_g * (1 - factor)),
        int(b * factor + bg_b * (1 - factor)),
    )

    # Recent events get a bright outline
    outline_color = (255, 255, 100) if recent else None
    outline_width = 2 if recent else 0

    # Draw marker shape based on event type
    sub_lower = sub_event.lower()
    if "air" in sub_lower or "drone" in sub_lower:
        # Circle for airstrikes
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=blended,
            outline=outline_color,
            width=outline_width,
        )
    elif "missile" in sub_lower or "shell" in sub_lower or "rocket" in sub_lower:
        # Diamond for missiles/shelling
        points = [(x, y - size), (x + size, y), (x, y + size), (x - size, y)]
        draw.polygon(points, fill=blended, outline=outline_color)
    elif "armed clash" in sub_lower or "attack" in sub_lower:
        # Triangle for ground combat
        points = [(x, y - size), (x + size, y + size), (x - size, y + size)]
        draw.polygon(points, fill=blended, outline=outline_color)
    elif "satellite" in sub_lower or "firms" in sub_lower or "thermal" in sub_lower:
        # Star/cross for satellite detections
        draw.line([(x - size, y), (x + size, y)], fill=blended, width=2)
        draw.line([(x, y - size), (x, y + size)], fill=blended, width=2)
    elif "seismic" in sub_lower or "earthquake" in sub_lower:
        # Ring for seismic
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            outline=blended,
            width=2,
        )
    elif "correlation" in sub_lower:
        # Filled ring for correlations
        draw.ellipse(
            [x - size - 2, y - size - 2, x + size + 2, y + size + 2],
            outline=(255, 255, 0),
            width=2,
        )
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=blended,
        )
    else:
        # Default circle
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=blended,
            outline=outline_color,
            width=outline_width,
        )


def draw_legend(draw, width, height, stats, date_range):
    """Draw legend box."""
    legend_x = width - 320
    legend_y = 15
    box_w = 305
    box_h = 30 + len([s for s, c in stats.get("by_actor_side", {}).items() if c > 0]) * 22 + 50

    # Semi-transparent background
    draw.rectangle(
        [legend_x, legend_y, legend_x + box_w, legend_y + box_h],
        fill=(10, 10, 20),
        outline=(60, 65, 80),
    )

    # Title
    y_pos = legend_y + 8
    draw.text((legend_x + 10, y_pos), "⚔️ MIDDLE EAST STRIKES MAP", fill=(255, 255, 255))
    y_pos += 22

    # Date range
    draw.text(
        (legend_x + 10, y_pos),
        f"{date_range['start']} → {date_range['end']}",
        fill=(150, 150, 160),
    )
    y_pos += 20

    # Actor sides
    for side, count in sorted(stats.get("by_actor_side", {}).items(), key=lambda x: -x[1]):
        if count == 0:
            continue
        color = SIDE_COLORS.get(side, SIDE_COLORS["unknown"])
        label = SIDE_LABELS.get(side, side.title())
        draw.rectangle(
            [legend_x + 10, y_pos + 2, legend_x + 24, y_pos + 16],
            fill=color,
        )
        draw.text((legend_x + 30, y_pos), f"{label}: {count:,}", fill=DARK_TEXT)
        y_pos += 22

    # Total
    y_pos += 5
    total = stats.get("total", 0)
    fatalities = stats.get("total_fatalities", 0)
    draw.text(
        (legend_x + 10, y_pos),
        f"Total: {total:,} events | {fatalities:,} fatalities",
        fill=(255, 255, 255),
    )


def draw_shape_legend(draw, width, height):
    """Draw marker shape legend at bottom-left."""
    x_start = 15
    y_start = height - 100
    box_w = 280
    box_h = 85

    draw.rectangle(
        [x_start, y_start, x_start + box_w, y_start + box_h],
        fill=(10, 10, 20),
        outline=(60, 65, 80),
    )

    y = y_start + 8
    draw.text((x_start + 10, y), "MARKER SHAPES", fill=(200, 200, 210))
    y += 18

    # Circle = airstrike
    draw.ellipse([x_start + 10, y + 2, x_start + 22, y + 14], fill=(100, 150, 255))
    draw.text((x_start + 30, y), "● Airstrike / Drone strike", fill=(160, 160, 170))
    y += 18

    # Diamond = missile
    cx, cy = x_start + 16, y + 8
    draw.polygon([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)], fill=(255, 140, 0))
    draw.text((x_start + 30, y), "◆ Missile / Shelling", fill=(160, 160, 170))
    y += 18

    # Triangle = ground
    cx, cy = x_start + 16, y + 4
    draw.polygon([(cx, cy - 5), (cx + 6, cy + 6), (cx - 6, cy + 6)], fill=(180, 180, 180))
    draw.text((x_start + 30, y), "▲ Ground combat / Attack", fill=(160, 160, 170))


def generate_strikes_map(data, config, output_path):
    """Generate the strikes map image."""
    if not HAS_PIL:
        return False

    strikes_cfg = config.get("strikes", {})
    map_cfg = {**MAP_DEFAULTS, **strikes_cfg}

    width = map_cfg["map_width"]
    height = map_cfg["map_height"]
    max_markers = map_cfg["max_markers"]
    highlight_hours = map_cfg["highlight_recent_hours"]

    events = data.get("events", [])
    stats = data.get("stats", {})
    date_range = data.get("config", {}).get("start_date", "?"), data.get("config", {}).get("end_date", "?")

    # Limit markers
    if len(events) > max_markers:
        events = events[:max_markers]

    img = Image.new("RGB", (width, height), DARK_BG)
    draw = ImageDraw.Draw(img)

    # Background
    draw_map_background(draw, width, height)

    # Calculate "recent" threshold
    now = datetime.now(timezone.utc)
    recent_cutoff = (now - timedelta(hours=highlight_hours)).strftime("%Y-%m-%d")

    # Draw events (oldest first so newest are on top)
    for event in reversed(events):
        lat = event.get("lat", 0)
        lon = event.get("lon", 0)

        # Skip events outside map bounds
        if not (MAP_BOUNDS["lat_min"] <= lat <= MAP_BOUNDS["lat_max"] and
                MAP_BOUNDS["lon_min"] <= lon <= MAP_BOUNDS["lon_max"]):
            continue

        x, y = latlon_to_pixel(lat, lon, width, height)
        side = event.get("actor1_side", "unknown")
        color = SIDE_COLORS.get(side, SIDE_COLORS["unknown"])
        size = get_marker_size(event.get("fatalities", 0))
        confidence = event.get("confidence", "medium")
        sub_event = event.get("sub_event_type", "")
        recent = event.get("date", "") >= recent_cutoff

        draw_strike_marker(draw, x, y, size, color, confidence, sub_event, recent)

    # Legend
    if map_cfg["show_legend"]:
        draw_legend(draw, width, height, stats, {"start": date_range[0], "end": date_range[1]})
        draw_shape_legend(draw, width, height)

    # Title bar
    title_text = f"MIDDLE EAST STRIKES MAP — {stats.get('total', 0):,} events since {date_range[0]}"
    draw.rectangle([0, 0, width, 30], fill=(10, 10, 20))
    draw.text((width // 2 - len(title_text) * 4, 8), title_text, fill=(255, 255, 255))

    # Footer
    footer = f"Generated {now.strftime('%Y-%m-%d %H:%M UTC')} | Sources: ACLED, NASA FIRMS, USGS, OSINT | Yellow outline = last {highlight_hours}h"
    draw.rectangle([0, height - 22, width, height], fill=(10, 10, 20))
    draw.text((10, height - 18), footer, fill=(120, 120, 130))

    img.save(output_path, "PNG", optimize=True)
    print(f"  [strikes-map] Saved {output_path} ({width}x{height}, {len(events)} markers)", file=sys.stderr)
    return True


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config.json> <state_dir> [--output path.png]", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    state_dir = sys.argv[2]

    # Parse --output flag
    output_path = os.path.join(state_dir, "strikes-map.png")
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    with open(config_path) as f:
        config = json.load(f)

    data_file = os.path.join(state_dir, "strikes-data.json")
    if not os.path.exists(data_file):
        print(f"  [strikes-map] No data file: {data_file} — run scan_strikes.py first", file=sys.stderr)
        sys.exit(1)

    with open(data_file) as f:
        data = json.load(f)

    if not data.get("events"):
        print("  [strikes-map] No events in data file", file=sys.stderr)
        sys.exit(1)

    success = generate_strikes_map(data, config, output_path)
    if success:
        # Output path for watcher integration
        print(output_path)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
