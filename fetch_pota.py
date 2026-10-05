#!/usr/bin/env python3
"""Fetch active POTA stations on the 20m, 40m, 15m and 17m bands in SSB.

Data source is the same endpoint the official web app (next.pota.app) uses.
That endpoint ignores all query parameters, so filtering happens here.
"""

from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Band edges in kHz, matching the band plan used by the official POTA web app.
BAND_PLAN: dict[str, tuple[int, int]] = {
    "20m": (14000, 14350),
    "40m": (7000, 7300),
    "15m": (21000, 21450),
    "17m": (18068, 18168),
}
MODES = {"SSB"}

# Which boxes go in which row, and how tall each row is.
LAYOUT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("row-tall", ("20m", "40m")),
    ("row-short", ("15m", "17m")),
)

API_URL = "https://api.pota.app/v1/spots"
OUTPUT_FILE = Path(__file__).resolve().parent / "pota_active_stations.html"
FETCH_ATTEMPTS = 3

STYLES = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: Arial, sans-serif; margin: 10px; background: #1a1a2e;
        color: #eee; overflow-x: hidden; max-width: 100%;
    }
    h1 { text-align: center; color: #00ff88; font-size: 1.5rem; }
    .timestamp { text-align: center; color: #888; margin-bottom: 15px; font-size: 0.9rem; }
    .timestamp.stale { color: #e74c3c; font-weight: bold; }
    .row {
        display: flex; gap: 15px; justify-content: center;
        margin-bottom: 15px; flex-wrap: wrap;
    }
    .box { flex: 1; min-width: 300px; background: #16213e; border-radius: 10px; padding: 12px; }
    .row-tall .box { max-height: 50vh; overflow-y: auto; }
    .row-short .box { max-height: 33vh; overflow-y: auto; }
    .box h2 {
        margin-top: 0; color: #00ff88; border-bottom: 2px solid #00ff88;
        padding-bottom: 8px; font-size: 1.2rem;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    thead th { background: #0f3460; padding: 8px; text-align: left; position: sticky; top: 0; }
    tbody td { padding: 6px 8px; border-bottom: 1px solid #333; }
    tbody tr:hover { background: #1f4068; }
    .count { color: #00ff88; font-weight: bold; }
    .table-wrapper {
        overflow: auto; -webkit-overflow-scrolling: touch;
        width: 100%; max-width: 100%;
    }

    .act-ref-cell, .freq-mode-cell { display: flex; flex-direction: column; }
    .act-label { font-weight: bold; color: #00ff88; }
    .ref-label { font-size: 0.85em; color: #aaa; }
    .freq-label { font-weight: bold; color: #e74c3c; }
    .mode-label { font-size: 0.85em; color: #aaa; }
    .park-label { white-space: normal; word-break: break-word; }
    .empty { color: #777; font-style: italic; text-align: center; padding: 14px 8px; }

    .col-act-ref { min-width: 120px; }
    .col-freq-mode { min-width: 100px; }
    .col-park { min-width: 200px; }

    @media (max-width: 480px) {
        body { margin: 5px; padding: 0; }
        h1 { font-size: 1.1rem; }
        .row { flex-direction: column; gap: 10px; margin-bottom: 10px; }
        .box { min-width: unset; width: 100%; padding: 6px; }
        .row-tall .box, .row-short .box { max-height: none; overflow-y: visible; }
        .box h2 { font-size: 0.95rem; padding-bottom: 5px; }
        table { font-size: 0.78rem; }
        thead th { padding: 5px 4px; }
        tbody td { padding: 5px 4px; }
        .col-act-ref { min-width: 0; }
        .col-freq-mode { min-width: 0; }
        .col-park { min-width: 0; }
    }

    @media (min-width: 481px) and (max-width: 1024px) {
        .box { min-width: 250px; }
        .row-tall .box { max-height: 45vh; }
        .row-short .box { max-height: 30vh; }
    }
"""


def _text(value: object) -> str:
    """Return a trimmed string for any API value, never None."""
    return value.strip() if isinstance(value, str) else ""


def _frequency(value: object) -> float | None:
    """Return the spot frequency in kHz, or None if it is unusable."""
    try:
        freq = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return freq if freq > 0 else None


def fetch_spots(attempts: int = FETCH_ATTEMPTS) -> list[dict]:
    """Fetch the current spot list, retrying a few times on transient errors."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                ["curl", "-sSf", "--max-time", "30", API_URL],
                capture_output=True,
                text=True,
                timeout=45,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"curl exit {result.returncode}")
            payload = json.loads(result.stdout)
            if not isinstance(payload, list):
                raise RuntimeError(f"expected a JSON list, got {type(payload).__name__}")
            return payload
        except (RuntimeError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
            last_error = exc
            print(f"  attempt {attempt}/{attempts} failed: {exc}", file=sys.stderr)
    raise RuntimeError(f"could not fetch spots after {attempts} attempts: {last_error}")


def spots_for_band(spots: list[dict], band: str) -> list[dict]:
    """Return de-duplicated SSB spots inside `band`, sorted by frequency."""
    low, high = BAND_PLAN[band]
    seen: dict[tuple[str, str, float, str], dict] = {}
    for spot in spots:
        activator = _text(spot.get("activator"))
        reference = _text(spot.get("reference")).upper()
        mode = _text(spot.get("mode")).upper()
        freq = _frequency(spot.get("frequency"))
        if not activator or not reference or freq is None:
            continue
        if mode not in MODES or not low <= freq < high:
            continue
        if reference.startswith("US-"):
            continue
        # The API is sorted newest first, so the first hit for a key is the
        # freshest one and later duplicates of the same station are dropped.
        # Callsigns and park references are case-insensitive, so they are
        # normalised before use as a key.
        seen.setdefault((activator.upper(), reference, freq, mode), spot)
    return sorted(seen.values(), key=lambda s: float(s["frequency"]))


def format_station_row(spot: dict) -> str:
    """Render one station as an HTML table row, escaping all API values."""
    activator = html.escape(_text(spot.get("activator")) or "N/A")
    reference = html.escape(_text(spot.get("reference")).upper() or "N/A")
    mode = html.escape(_text(spot.get("mode")).upper() or "-")
    frequency = html.escape(f"{float(spot['frequency']):.1f}")
    park = html.escape(_text(spot.get("name"))[:50]) or "N/A"
    return (
        "<tr>"
        '<td class="col-act-ref"><div class="act-ref-cell">'
        f'<span class="act-label">{activator}</span>'
        f'<span class="ref-label">{reference}</span>'
        "</div></td>"
        '<td class="col-freq-mode"><div class="freq-mode-cell">'
        f'<span class="freq-label">{frequency}</span>'
        f'<span class="mode-label">{mode}</span>'
        "</div></td>"
        f'<td class="col-park"><span class="park-label">{park}</span></td>'
        "</tr>"
    )


def generate_html(band_data: dict[str, list[dict]], generated_at: datetime) -> str:
    """Render the full dashboard page."""
    rows: list[str] = []
    for row_class, bands in LAYOUT:
        boxes: list[str] = []
        for band in bands:
            spots = band_data.get(band, [])
            if spots:
                body = "\n".join(f"                {format_station_row(s)}" for s in spots)
            else:
                body = '                <tr><td class="empty" colspan="3">No stations</td></tr>'
            boxes.append(
                f"""
        <div class="box">
            <h2>{html.escape(band.upper())} - <span class="count">{len(spots)} stations</span></h2>
            <div class="table-wrapper">
            <table>
                <thead><tr>
                    <th scope="col">Activator</th>
                    <th scope="col">Frequency</th>
                    <th scope="col">Park Name</th>
                </tr></thead>
                <tbody>
{body}
                </tbody>
            </table>
            </div>
        </div>
"""
            )
        rows.append(f'    <div class="row {row_class}">\n' + "".join(boxes) + "    </div>\n")

    stamp = generated_at.isoformat(timespec="seconds")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POTA Active Stations - SSB</title>
    <style>{STYLES}    </style>
</head>
<body>
    <h1>POTA Active Stations - SSB</h1>
    <p class="timestamp">Generated: {html.escape(stamp)}</p>
{"".join(rows)}</body>
</html>
"""


def write_atomic(path: Path, content: str) -> None:
    """Write `content` to `path` without ever leaving a partial file behind."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        # mkstemp creates 0600; the dashboard has to stay world-readable so the
        # web server can serve it after run_fetch.sh copies it.
        tmp_path.chmod(0o644)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def main() -> int:
    generated_at = datetime.now().astimezone()
    modes = ", ".join(sorted(MODES))
    print(f"[{generated_at.isoformat(timespec='seconds')}] Fetching {API_URL}")
    print(f"Bands: {', '.join(BAND_PLAN)} | Modes: {modes}")

    try:
        spots = fetch_spots()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Leaving {OUTPUT_FILE.name} untouched.", file=sys.stderr)
        return 1

    band_data = {band: spots_for_band(spots, band) for band in BAND_PLAN}
    for band, band_spots in band_data.items():
        print(f"  {band:>4}: {len(band_spots)} stations")

    write_atomic(OUTPUT_FILE, generate_html(band_data, generated_at))
    print(f"Saved {sum(len(v) for v in band_data.values())} rows to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
