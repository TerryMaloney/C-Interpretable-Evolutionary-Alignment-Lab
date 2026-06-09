"""
Generate interactive Folium map for quick visual inspection of clustering results.

Reads from output/layers/*.geojson
Outputs output/anomaly_map.html

Layers are color-coded by category. Click any point for details.
Use this for initial visual QC before Phase 2 Mapbox/Deck.gl build.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import OUTPUT_DIR, get_logger, load_registry

log = get_logger("generate_map")

LAYERS_DIR = OUTPUT_DIR / "layers"
MAP_OUTPUT = OUTPUT_DIR / "anomaly_map.html"

# Color scheme per category
CATEGORY_COLORS = {
    "uap": "#FF4444",
    "marine": "#4488FF",
    "geophysical": "#44AA44",
    "em_disturbance": "#FF8800",
    "radiation": "#FF00FF",
    "infrastructure": "#888888",
    "earth_lights": "#FFFF00",
    "anomalous_incident": "#FF6644",
    "acoustic": "#00FFFF",
    "nav_disruption": "#AAFFAA",
    "historical": "#CCAA88",
    "manual": "#CCCCCC",
    "unknown": "#FFFFFF",
}

# Max points per layer for performance (folium struggles with >50k points)
MAX_POINTS_PER_LAYER = 10000

TIER_RADIUS = {1: 6, 2: 5, 3: 4}  # Tier 1 = larger dots


def main():
    log.info("=== generate_map.py ===")

    try:
        import folium
        from folium.plugins import MarkerCluster
    except ImportError:
        log.error("folium not installed. Run: pip install folium")
        return

    registry = load_registry()

    m = folium.Map(
        location=[38.0, -97.0],
        zoom_start=4,
        tiles="CartoDB dark_matter",
    )

    layer_files = sorted(LAYERS_DIR.glob("*.geojson"))
    if not layer_files:
        log.warning(f"No layer files in {LAYERS_DIR}. Run the pipeline first.")
        return

    total_points = 0
    feature_groups = {}

    for path in layer_files:
        layer_name = path.stem
        layer_meta = registry.get("layers", {}).get(layer_name, {})
        display_name = layer_meta.get("name", layer_name)
        tier = layer_meta.get("tier", 2)
        category = layer_meta.get("category", "unknown")

        color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["unknown"])
        radius = TIER_RADIUS.get(tier, 4)

        try:
            with open(path) as f:
                gj = json.load(f)
        except Exception as exc:
            log.warning(f"Failed to load {path.name}: {exc}")
            continue

        features = gj.get("features", [])
        if not features:
            continue

        # Subsample if needed
        if len(features) > MAX_POINTS_PER_LAYER:
            import random
            features = random.sample(features, MAX_POINTS_PER_LAYER)
            log.info(f"  {layer_name}: subsampled to {MAX_POINTS_PER_LAYER}")

        fg = folium.FeatureGroup(name=f"[T{tier}] {display_name} ({len(features)})", show=True)

        for feat in features:
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]

            props = feat.get("properties", {})
            popup_lines = [f"<b>{display_name}</b>"]
            for key in ("datetime", "notes", "source", "confidence", "magnitude", "species",
                        "facility_name", "event_type", "cause", "station_name"):
                val = props.get(key)
                if val and str(val).strip():
                    popup_lines.append(f"<b>{key}:</b> {str(val)[:200]}")

            popup_html = "<br>".join(popup_lines)

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                opacity=0.9,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{layer_name}: {props.get('datetime', '') or props.get('notes', '')[:60]}",
            ).add_to(fg)

            total_points += 1

        fg.add_to(m)
        log.info(f"  Added layer: {layer_name} ({len(features)} points)")

    # Add zone rectangles
    zones_meta = registry.get("zones_of_interest", {})
    for zone_id, zone in zones_meta.items():
        bbox = zone.get("bbox", {})
        if not bbox:
            continue
        folium.Rectangle(
            bounds=[
                [bbox["min_lat"], bbox["min_lon"]],
                [bbox["max_lat"], bbox["max_lon"]],
            ],
            color="white",
            fill=False,
            weight=2,
            dash_array="5 5",
            tooltip=f"Zone {zone_id}: {zone['name']}",
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: rgba(0,0,0,0.8); color: white; padding: 12px;
                border-radius: 8px; font-family: monospace; font-size: 12px;">
        <b>ANOMALY MAP — LAYER LEGEND</b><br>
    """
    for cat, color in CATEGORY_COLORS.items():
        if cat not in ("unknown", "manual"):
            legend_html += f'<span style="color:{color}">■</span> {cat}<br>'
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    MAP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(MAP_OUTPUT))
    log.info(f"\nMap saved → {MAP_OUTPUT}")
    log.info(f"Total points rendered: {total_points:,}")
    log.info("Open in browser to inspect clustering visually.")


if __name__ == "__main__":
    main()
