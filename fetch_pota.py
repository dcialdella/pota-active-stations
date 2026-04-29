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
    try:
        freq = float(frequency)
        frequency = f"{freq:.1f}"
    except (ValueError, TypeError):
        pass
    return (
        f'<tr>'
        f'<td class="col-act-ref"><div class="act-ref-cell">'
        f'<span class="act-label">{activator}</span>'
        f'<span class="ref-label">{reference}</span>'
        f'</div></td>'
        f'<td class="col-freq-mode"><div class="freq-mode-cell">'
        f'<span class="freq-label">{frequency}</span>'
        f'<span class="mode-label">{mode}</span>'
        f'</div></td>'
        f'<td><span class="park-label">{name[:50]}</span></td>'
        f'</tr>'
    )


def generate_html(band_data: dict) -> str:
    """Generate HTML page with 2 rows of horizontal boxes."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POTA Active Stations - SSB</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: Arial, sans-serif; margin: 10px; background: #1a1a2e; color: #eee; overflow-x: hidden; max-width: 100vw; }}
        h1 {{ text-align: center; color: #00ff88; font-size: 1.5rem; }}
        .timestamp {{ text-align: center; color: #888; margin-bottom: 15px; font-size: 0.9rem; }}
        .row {{ display: flex; gap: 15px; justify-content: center; margin-bottom: 15px; flex-wrap: wrap; }}
        .box {{ flex: 1; min-width: 300px; background: #16213e; border-radius: 10px; padding: 12px; }}
        .row-tall .box {{ max-height: 50vh; overflow-y: auto; }}
        .row-short .box {{ max-height: 33vh; overflow-y: auto; }}
        .box h2 {{ margin-top: 0; color: #00ff88; border-bottom: 2px solid #00ff88; padding-bottom: 8px; font-size: 1.2rem; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ background: #0f3460; padding: 8px; text-align: left; }}
        td {{ padding: 6px 8px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #1f4068; }}
        .count {{ color: #00ff88; font-weight: bold; }}
        .table-wrapper {{ overflow-x: auto; -webkit-overflow-scrolling: touch; width: 100%; max-width: 100%; }}

        .act-ref-cell, .freq-mode-cell {{ display: flex; flex-direction: column; }}
        .act-label {{ font-weight: bold; color: #00ff88; }}
        .ref-label {{ font-size: 0.85em; color: #aaa; }}
        .freq-label {{ font-weight: bold; color: #e74c3c; }}
        .mode-label {{ font-size: 0.85em; color: #aaa; }}
        .park-label {{ white-space: normal; word-break: break-word; }}

        .col-act-ref {{ min-width: 120px; }}
        .col-freq-mode {{ min-width: 100px; }}
        .col-park {{ min-width: 200px; }}

        @media (max-width: 480px) {{
            body {{ margin: 5px; padding: 0; }}
            h1 {{ font-size: 1.1rem; }}
            .row {{ flex-direction: column; gap: 10px; margin-bottom: 10px; }}
            .box {{ min-width: unset; width: 100%; padding: 6px; }}
            .row-tall .box, .row-short .box {{ max-height: none; overflow-y: visible; }}
            .box h2 {{ font-size: 0.95rem; padding-bottom: 5px; }}
            table {{ font-size: 0.78rem; }}
            th {{ padding: 5px 4px; }}
            td {{ padding: 5px 4px; }}
            .col-act-ref {{ min-width: 0; }}
            .col-freq-mode {{ min-width: 0; }}
            .col-park {{ min-width: 0; }}
        }}

        @media (min-width: 481px) and (max-width: 1024px) {{
            .box {{ min-width: 250px; }}
            .row-tall .box {{ max-height: 45vh; }}
            .row-short .box {{ max-height: 30vh; }}
        }}
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
            <div class="table-wrapper">
            <table>
                <tr><th>Activator</th><th>Frequency</th><th>Park Name</th></tr>
"""
        for spot in spots:
            html += f"                {format_station_row(spot)}\n"
        html += """
            </table>
            </div>
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
            <div class="table-wrapper">
            <table>
                <tr><th>Activator</th><th>Frequency</th><th>Park Name</th></tr>
"""
        for spot in spots:
            html += f"                {format_station_row(spot)}\n"
        html += """
            </table>
            </div>
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