#!/usr/bin/env python3
"""Fetch active POTA stations on 20m and 40m bands."""

import json
import subprocess
from datetime import datetime

BANDS = ["20m", "40m", "15m", "17m"]
FREQ_RANGES = {"20m": (14000, 14350), "40m": (7000, 7200), "15m": (21000, 21450), "17m": (18068, 18168)}
MODES = ["SSB"]
OUTPUT_FILE = "pota_active_stations.html"
API_URL = "https://api.pota.app/spot/activator"


def fetch_all_spots() -> list[dict]:
    """Fetch all spots using curl."""
    result = subprocess.run(
        ["curl", "-s", API_URL],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def filter_by_band(spots: list[dict], band: str) -> list[dict]:
    """Filter spots by frequency range for a band."""
    min_freq, max_freq = FREQ_RANGES[band]
    filtered = [
        s for s in spots
        if s.get("mode", "").upper() == "SSB"
        and not s.get("reference", "").startswith("US-")
        and s.get("frequency")
        and min_freq <= float(s.get("frequency")) < max_freq
    ]
    return sorted(filtered, key=lambda s: float(s.get("frequency", 0)))


def format_station_row(spot: dict) -> str:
    """Format a station row for HTML table."""
    activator = spot.get("activator", "N/A")
    reference = spot.get("reference", "N/A")
    frequency = spot.get("frequency", "N/A")
    mode = spot.get("mode", "")
    name = spot.get("name", "N/A")
    location = spot.get("locationDesc", "")
    try:
        freq = float(frequency)
        frequency = f"{freq:.1f}"
    except (ValueError, TypeError):
        pass
    return f"<tr><td>{activator}</td><td>{reference}</td><td><b style='color:red'>{frequency}</b></td><td>{mode}</td><td>{name[:40]}</td><td>{location}</td></tr>"


def generate_html(band_data: dict) -> str:
    """Generate HTML page with 2 rows of horizontal boxes."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POTA Active Stations - SSB</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ text-align: center; color: #00ff88; }}
        .timestamp {{ text-align: center; color: #888; margin-bottom: 20px; }}
        .row {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
        .box {{ flex: 1; min-width: 400px; background: #16213e; border-radius: 10px; padding: 15px; }}
        .row-tall .box {{ max-height: 50vh; overflow-y: auto; }}
        .row-short .box {{ max-height: 33vh; overflow-y: auto; }}
        .box h2 {{ margin-top: 0; color: #00ff88; border-bottom: 2px solid #00ff88; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #0f3460; padding: 10px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #1f4068; }}
        .count {{ color: #00ff88; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>POTA Active Stations - SSB</h1>
    <p class="timestamp">Generated: {datetime.now().isoformat()}</p>
"""
    # First row: 20m, 40m (taller)
    html += '    <div class="row row-tall">\n'
    for band in BANDS[:2]:
        spots = band_data.get(band, [])
        html += f"""
        <div class="box">
            <h2>{band.upper()} - <span class="count">{len(spots)} stations</span></h2>
            <table>
                <tr><th>Activator</th><th>Reference</th><th>Frequency</th><th>Mode</th><th>Park Name</th><th>Location</th></tr>
"""
        for spot in spots:
            html += f"                {format_station_row(spot)}\n"
        html += """
            </table>
        </div>
"""
    html += '    </div>\n'
    
    # Second row: 15m, 17m (mas corta)
    html += '    <div class="row row-short">\n'
    for band in BANDS[2:]:
        spots = band_data.get(band, [])
        html += f"""
        <div class="box">
            <h2>{band.upper()} - <span class="count">{len(spots)} stations</span></h2>
            <table>
                <tr><th>Activator</th><th>Reference</th><th>Frequency</th><th>Mode</th><th>Park Name</th><th>Location</th></tr>
"""
        for spot in spots:
            html += f"                {format_station_row(spot)}\n"
        html += """
            </table>
        </div>
"""
    html += '    </div>\n'
    html += """
</body>
</html>
"""
    return html


def main():
    print(f"Fetching POTA active stations for bands: {', '.join(BANDS)} and modes: {', '.join(MODES)}...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    all_spots = fetch_all_spots()
    band_data = {}
    
    for band in BANDS:
        spots = filter_by_band(all_spots, band)
        print(f"Found {len(spots)} spots on {band}")
        band_data[band] = spots

    html_content = generate_html(band_data)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html_content)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()