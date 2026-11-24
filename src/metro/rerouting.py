"""US-2: find a rider's fastest route, and the new route when stations close.

CECS 427 concept: weighted shortest paths. NetworkX's shortest path (Dijkstra's
algorithm) finds the route with the fewest total minutes, using each segment's
"weight" (scheduled travel time). Closing stations removes them from a copy of
the network, and we search again to see the detour and how many minutes it adds.

Stations are passed by their station ID (e.g. "80122S" on LA data, "C" on the
sample network), not by name.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import networkx as nx

from .graph import close_stations


def find_route(G: nx.Graph, start: str, end: str) -> Optional[Tuple[List[str], float]]:
    """Fastest route from start to end as (list of station IDs, minutes).

    Returns None if the two stations aren't connected.
    Raises ValueError if either station isn't in the network, so a typo
    is never mistaken for an unreachable trip.
    """
    # Check if the starting and ending stations exist
    _check_stations(G, [start, end])

    try:
        # Find the fastest path and its total travel time in one search
        time, path = nx.single_source_dijkstra(G, start, end, weight="weight")
        return path, time

    except nx.NetworkXNoPath:
        # Return None if the stations are not connected
        return None


def reroute(G: nx.Graph, start: str, end: str, closed_stations: Iterable[str]) -> dict:
    """Compare the normal route with the route after closing some stations.

    Returns a dict:
        original       (path, minutes) before the closure, or None if no route
        alternative    (path, minutes) after the closure, or None if no route
        extra_minutes  minutes the closure adds, or None if either trip is impossible

    closed_stations must be a list (or other collection) of station IDs.
    Raises ValueError for unknown station IDs or a single string instead of a list.
    """
    if isinstance(closed_stations, str):
        raise ValueError("closed_stations must be a list of station IDs, e.g. ['C'], not a single string")
    closed_stations = list(closed_stations)
    _check_stations(G, [start, end] + closed_stations)

    # Find the original route before closing stations
    original = find_route(G, start, end)

    # If the trip starts or ends at a closed station, there is no alternative
    if start in closed_stations or end in closed_stations:
        alternative = None
    else:
        # Remove the closed stations from a copy of the graph
        updated_graph = close_stations(G, closed_stations)

        # Find a new route that avoids the closed stations
        alternative = find_route(updated_graph, start, end)

    # Check how many extra minutes the new route takes
    extra_minutes = None

    if original is not None and alternative is not None:
        extra_minutes = alternative[1] - original[1]

    return {
        "original": original,
        "alternative": alternative,
        "extra_minutes": extra_minutes
    }


def _check_stations(G: nx.Graph, stations: Iterable[str]) -> None:
    """Raise ValueError listing any station IDs that aren't in the network."""
    unknown = [s for s in stations if s not in G]
    if unknown:
        raise ValueError(f"unknown station ID(s): {', '.join(map(str, unknown))}")
