"""Turn a GTFS transit schedule into our rail network (an nx.Graph).

GTFS is the standard format transit agencies publish their schedules in (LA Metro included).
It's a folder or zip of CSV text files. We read four of them:
    routes.txt      the lines, and what kind of vehicle runs each one (route_type)
    stops.txt       stations and their platforms, with names and coordinates
    trips.txt       individual vehicle runs, each belonging to one line
    stop_times.txt  for each run, the stops in order with arrival/departure times

GTFS has no list of edges, so we build them from the schedule:
1. Keep rail lines only (route_type 0 light rail, 1 subway, 2 rail). Buses are dropped.
2. Merge platforms into their parent station, so a transfer station is ONE node.
3. Two consecutive stops on a run become a segment. Its time is the departure from the
   first stop to the arrival at the next, so time waiting at a platform isn't counted.
4. A segment runs many times a day with slightly different times, so its weight is the
   MEDIAN of all observed times (one odd late-night run doesn't skew it).

Reference: https://gtfs.org/schedule/reference/
"""

from __future__ import annotations

import csv
import io
import statistics
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import networkx as nx

from metro.graph import add_segment

RAIL_ROUTE_TYPES = {0, 1, 2}  # 0 = light rail, 1 = subway, 2 = rail; 3 (bus) and others are dropped


def load_network(source: Union[str, Path]) -> nx.Graph:
    """Build the rail network from a GTFS feed (a folder or a .zip file)."""
    source = Path(source)
    G = nx.Graph()

    # Step 1: rail lines only, and the trips that run on them.
    rail_lines = {}  # route_id -> line name shown to users, e.g. "A Line"
    for row in _read(source, "routes.txt"):
        if _int(row.get("route_type")) in RAIL_ROUTE_TYPES:
            rail_lines[row["route_id"]] = (row.get("route_short_name") or row.get("route_long_name") or row["route_id"]).strip()
    trip_line = {t["trip_id"]: rail_lines[t["route_id"]] for t in _read(source, "trips.txt") if t["route_id"] in rail_lines}

    # Step 2: map every stop (platform) to its parent station.
    stops = {s["stop_id"]: s for s in _read(source, "stops.txt")}

    def station_of(stop_id: str) -> str:
        while stops.get(stop_id, {}).get("parent_station"):
            stop_id = stops[stop_id]["parent_station"]
        return stop_id

    # Step 3: collect every stop visit of every rail trip, then sort each trip by stop order.
    visits: Dict[str, List[Tuple[int, str, Optional[int], Optional[int]]]] = {}
    for st in _read(source, "stop_times.txt"):
        if st["trip_id"] in trip_line:
            visits.setdefault(st["trip_id"], []).append(
                (int(st["stop_sequence"]), station_of(st["stop_id"]), _seconds(st.get("arrival_time")), _seconds(st.get("departure_time")))
            )

    # Consecutive stops = one observed ride over a segment. Record its minutes.
    observed: Dict[Tuple[str, str, str], List[float]] = {}  # (station, station, line) -> minutes seen
    for trip_id, rows in visits.items():
        rows.sort()
        for (_, a, _, leave_a), (_, b, arrive_b, _) in zip(rows, rows[1:]):
            if a == b or leave_a is None or arrive_b is None or arrive_b < leave_a:
                continue  # same station twice, missing times, or bad data: skip
            key = (min(a, b), max(a, b), trip_line[trip_id])  # sorted pair: A->B and B->A count together
            observed.setdefault(key, []).append((arrive_b - leave_a) / 60)

    # Step 4: one edge per segment, weighted by the median time.
    for (a, b, line), minutes in observed.items():
        for station in (a, b):
            if station not in G:
                info = stops.get(station, {})
                G.add_node(station, name=(info.get("stop_name") or station).strip(), lat=_float(info.get("stop_lat")), lon=_float(info.get("stop_lon")))
        add_segment(G, a, b, round(statistics.median(minutes), 2), route=line)

    return G


# ----- small helpers ---------------------------------------------------------------------


def _read(source: Path, name: str) -> List[dict]:
    """Rows of one GTFS file as dictionaries, from a folder or a zip."""
    if source.is_dir():
        path = source / name
        if not path.exists():
            raise FileNotFoundError(f"{name} is missing from {source}")
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    with zipfile.ZipFile(source) as z:
        # Some agencies put the files inside a folder in the zip.
        match = next((n for n in z.namelist() if n == name or n.endswith("/" + name)), None)
        if match is None:
            raise FileNotFoundError(f"{name} is missing from {source}")
        with z.open(match) as raw:
            return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")))


def _seconds(hms: Optional[str]) -> Optional[int]:
    """'08:07:00' -> 29220. GTFS hours can go past 24 for after-midnight runs (e.g. '25:10:00'). Blank -> None."""
    hms = (hms or "").strip()
    if not hms:
        return None
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def _int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
