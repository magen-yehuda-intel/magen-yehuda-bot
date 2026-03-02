#!/usr/bin/env python3
"""
generate-strikes-map.py — High-quality strikes map using Cartopy + Matplotlib

Renders a dark-themed map of the Middle East with strike markers on real geography.
"""

import json
import os
import sys
import math
from datetime import datetime, timezone, timedelta

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.colors import to_rgba
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from cartopy.io import shapereader
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    print(f"  [strikes-map] Missing dependency: {e}", file=sys.stderr)

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

MAP_DEFAULTS = {
    "map_width": 1600,
    "map_height": 1000,
    "max_markers": 50000,
    "highlight_recent_hours": 48,
}

# Map extent: [lon_min, lon_max, lat_min, lat_max]
MAP_EXTENT = [28, 65, 10, 42]

SIDE_COLORS = {
    "israel":     "#0078FF",
    "iran":       "#DC1E1E",
    "iran_proxy": "#FF8C00",
    "us":         "#003296",
    "syria":      "#666666",
    "gulf":       "#00B464",
    "unknown":    "#B4B4B4",
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

SIDE_MARKERS = {
    "israel": "o",
    "iran": "D",
    "iran_proxy": "^",
    "us": "s",
    "syria": "v",
    "gulf": "p",
    "unknown": ".",
}


def get_marker_size(fatalities, base=6):
    if fatalities <= 0:
        return base
    return min(base + math.sqrt(fatalities) * 2, 40)


def generate_strikes_map(data, config, output_path):
    if not HAS_DEPS:
        return False

    strikes_cfg = config.get("strikes", {})
    map_cfg = {**MAP_DEFAULTS, **strikes_cfg}

    w_px = map_cfg["map_width"]
    h_px = map_cfg["map_height"]
    dpi = 150
    fig_w = w_px / dpi
    fig_h = h_px / dpi
    highlight_hours = map_cfg["highlight_recent_hours"]
    max_markers = map_cfg["max_markers"]

    events = data.get("events", [])
    stats = data.get("stats", {})
    date_start = data.get("config", {}).get("start_date", "?")
    date_end = data.get("config", {}).get("end_date", "?")

    if len(events) > max_markers:
        events = events[:max_markers]

    now = datetime.now(timezone.utc)
    recent_cutoff = (now - timedelta(hours=highlight_hours)).strftime("%Y-%m-%d")

    # ── Create figure ──
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi, facecolor='#12121C')
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.88], projection=ccrs.PlateCarree())
    ax.set_extent(MAP_EXTENT, crs=ccrs.PlateCarree())
    ax.set_facecolor('#0F1932')

    # ── Geography ──
    ax.add_feature(cfeature.LAND, facecolor='#1E2330', edgecolor='none', zorder=1)
    ax.add_feature(cfeature.OCEAN, facecolor='#0F1932', zorder=0)
    ax.add_feature(cfeature.BORDERS, edgecolor='#3A3F50', linewidth=0.5, zorder=2)
    ax.add_feature(cfeature.COASTLINE, edgecolor='#3A3F50', linewidth=0.3, zorder=2)
    ax.add_feature(cfeature.LAKES, facecolor='#0F1932', edgecolor='#3A3F50', linewidth=0.3, zorder=2)

    # Gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='#252A3A', alpha=0.7,
                       xlocs=range(30, 66, 5), ylocs=range(10, 43, 5))
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 7, 'color': '#5A5F70'}
    gl.ylabel_style = {'size': 7, 'color': '#5A5F70'}

    # ── Country labels ──
    country_labels = {
        'IRAN': (53, 33), 'IRAQ': (43.5, 33.5), 'SYRIA': (38.5, 35),
        'SAUDI\nARABIA': (45, 24), 'YEMEN': (47, 15.5), 'TURKEY': (35, 39),
        'EGYPT': (30, 27), 'ISRAEL': (35, 31.5), 'JORDAN': (37, 31),
        'KUWAIT': (47.5, 29.5), 'UAE': (54, 24), 'QATAR': (51.2, 25.3),
        'OMAN': (57, 21), 'BAHRAIN': (50.5, 26), 'PAKISTAN': (63, 28),
        'AFGHANISTAN': (63, 34), 'LEBANON': (35.8, 33.8),
    }
    for name, (lon, lat) in country_labels.items():
        if MAP_EXTENT[0] <= lon <= MAP_EXTENT[1] and MAP_EXTENT[2] <= lat <= MAP_EXTENT[3]:
            ax.text(lon, lat, name, transform=ccrs.PlateCarree(),
                    fontsize=6, color='#4A4F60', ha='center', va='center',
                    fontweight='bold', style='italic', zorder=3)

    # ── Plot strikes by side (oldest first → newest on top) ──
    by_side = {}
    for event in reversed(events):
        side = event.get("actor1_side", "unknown")
        if side not in by_side:
            by_side[side] = {"lons": [], "lats": [], "sizes": [], "alphas": [], "edge": []}
        lat = event.get("lat", 0)
        lon = event.get("lon", 0)
        if not (MAP_EXTENT[2] <= lat <= MAP_EXTENT[3] and MAP_EXTENT[0] <= lon <= MAP_EXTENT[1]):
            continue

        conf = event.get("confidence", "medium")
        alpha = {"high": 0.85, "medium": 0.55, "low": 0.25}.get(conf, 0.55)
        recent = event.get("date", "") >= recent_cutoff
        size = get_marker_size(event.get("fatalities", 0))

        by_side[side]["lons"].append(lon)
        by_side[side]["lats"].append(lat)
        by_side[side]["sizes"].append(size)
        by_side[side]["alphas"].append(min(alpha + (0.15 if recent else 0), 1.0))
        by_side[side]["edge"].append('#FFFF64' if recent else 'none')

    for side, d in by_side.items():
        if not d["lons"]:
            continue
        color = SIDE_COLORS.get(side, SIDE_COLORS["unknown"])
        marker = SIDE_MARKERS.get(side, "o")
        # Scatter with per-point alpha via RGBA
        rgba = to_rgba(color)
        colors = [(rgba[0], rgba[1], rgba[2], a) for a in d["alphas"]]

        ax.scatter(d["lons"], d["lats"], s=d["sizes"], c=colors,
                   marker=marker, edgecolors=d["edge"], linewidths=0.3,
                   transform=ccrs.PlateCarree(), zorder=5 + list(SIDE_COLORS.keys()).index(side)
                   if side in SIDE_COLORS else 5)

    # ── Title ──
    total = stats.get("total", len(events))
    fatalities = stats.get("total_fatalities", 0)
    title = f"⚔️  MIDDLE EAST STRIKES MAP — {total:,} events since {date_start}"
    fig.text(0.5, 0.96, title, ha='center', va='top', fontsize=11, color='white',
             fontweight='bold', path_effects=[pe.withStroke(linewidth=2, foreground='#12121C')])

    # ── Legend ──
    legend_elements = []
    from matplotlib.lines import Line2D
    for side in ["israel", "us", "iran", "iran_proxy", "syria", "gulf", "unknown"]:
        count = stats.get("by_actor_side", {}).get(side, 0)
        if count == 0:
            continue
        color = SIDE_COLORS[side]
        marker = SIDE_MARKERS[side]
        label = f"{SIDE_LABELS[side]}: {count:,}"
        legend_elements.append(
            Line2D([0], [0], marker=marker, color='none', markerfacecolor=color,
                   markeredgecolor='#3A3F50', markersize=7, label=label)
        )

    if legend_elements:
        leg = ax.legend(handles=legend_elements, loc='upper right', fontsize=6.5,
                        facecolor='#0A0A14', edgecolor='#3A3F50', labelcolor='#C8C8D2',
                        framealpha=0.9, borderpad=0.8, handletextpad=0.5)
        leg.set_zorder(20)

    # ── Shape legend ──
    shape_elements = [
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#6496FF', markersize=6,
               label='● Airstrike / Drone'),
        Line2D([0], [0], marker='D', color='none', markerfacecolor='#FF8C00', markersize=6,
               label='◆ Missile / Shelling'),
        Line2D([0], [0], marker='^', color='none', markerfacecolor='#B4B4B4', markersize=6,
               label='▲ Ground / Attack'),
        Line2D([0], [0], marker='s', color='none', markerfacecolor='#003296', markersize=6,
               label='■ US Military'),
    ]
    shape_leg = fig.legend(handles=shape_elements, loc='lower left', fontsize=5.5,
                           facecolor='#0A0A14', edgecolor='#3A3F50', labelcolor='#A0A0B0',
                           framealpha=0.9, bbox_to_anchor=(0.02, 0.04))
    shape_leg.set_zorder(20)

    # ── Footer ──
    footer = (f"Generated {now.strftime('%Y-%m-%d %H:%M UTC')} | "
              f"Sources: ACLED, NASA FIRMS, USGS, OSINT | "
              f"Total: {total:,} events · {fatalities:,} fatalities | "
              f"Yellow outline = last {highlight_hours}h")
    fig.text(0.5, 0.01, footer, ha='center', fontsize=5.5, color='#78788A')

    # ── Save ──
    fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor(),
                bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    print(f"  [strikes-map] Saved {output_path} ({w_px}x{h_px}, {len(events)} markers)", file=sys.stderr)
    return True


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config.json> <state_dir> [--output path.png]", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    state_dir = sys.argv[2]

    output_path = os.path.join(state_dir, "strikes-map.png")
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    with open(config_path) as f:
        config = json.load(f)

    data_file = os.path.join(state_dir, "strikes-data.json")
    if not os.path.exists(data_file):
        print(f"  [strikes-map] No data file: {data_file}", file=sys.stderr)
        sys.exit(1)

    with open(data_file) as f:
        data = json.load(f)

    if not data.get("events"):
        print("  [strikes-map] No events in data", file=sys.stderr)
        sys.exit(1)

    success = generate_strikes_map(data, config, output_path)
    if success:
        print(output_path)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
