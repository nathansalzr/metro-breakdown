"""US-3: find the stations the network depends on most.

CECS 427 concepts:
- Betweenness centrality: for every pair of stations, find the fastest route between them.
  A station's betweenness is how many of those routes pass through it. High betweenness
  means many trips depend on that station, so closing it hurts the most riders' routes.
- Articulation point: a station that, if closed, splits the network into separate pieces.
  Some riders could no longer reach some stations at all. These are single points of failure.
- Bridge: the same idea for a segment. Removing it splits the network.

Stations are passed and returned by station ID, the same as in rerouting.py.
Use G.nodes[station_id]["name"] to show a station's name.
"""

from __future__ import annotations

from typing import List, Set, Tuple

import networkx as nx

from .graph import close_stations


def top_stations(G: nx.Graph, k: int, normalized: bool = True) -> List[Tuple[str, str, float]]:
    """The k stations with the highest betweenness, as (station_id, name, score), highest first.

    Routes are weighted by travel time, so "between" means on the fastest route.
    normalized=True gives each score as a share of all station pairs (0 to 1).
    normalized=False gives the raw count of fastest routes through the station.
    Ties are listed alphabetically by name so results are always in the same order.
    Scores are rounded to 6 decimals so tiny float differences can't reorder ties.

    Uses nx.betweenness_centrality with weight="weight", which counts fastest routes
    (by minutes) instead of fewest stops, because riders care about time.
    """
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    scores = nx.betweenness_centrality(G, weight="weight", normalized=normalized)
    ranked = sorted(
        ((sid, G.nodes[sid].get("name", sid), round(score, 6)) for sid, score in scores.items()),
        key=lambda row: (-row[2], row[1]),
    )
    return ranked[:k]


def single_points_of_failure(G: nx.Graph) -> dict:
    """Stations and segments whose closure would split the network.

    Returns {"stations": [...], "segments": [(u, v), ...]}, both sorted. Both lists are
    empty when the network has no single point of failure (for example, a loop).

    Uses nx.articulation_points for stations and nx.bridges for segments. Both find every
    single point of failure in one pass instead of trying each closure one at a time.
    """
    return {
        "stations": sorted(nx.articulation_points(G)),
        "segments": sorted(tuple(sorted(edge)) for edge in nx.bridges(G)),
    }


def pieces_after_closing(G: nx.Graph, station: str) -> List[Set[str]]:
    """The connected pieces left after closing one station, largest first.

    One piece means everyone can still reach everyone. More than one means the closure
    cut some stations off. If the closed station was the only one, the result is empty.
    The original network is not changed.

    Uses close_stations (a copy without the station) and nx.connected_components, which
    groups the stations that can still reach each other.
    """
    if station not in G:
        raise ValueError(f"unknown station ID: {station}")
    pieces = nx.connected_components(close_stations(G, [station]))
    return sorted(pieces, key=lambda piece: (-len(piece), min(piece)))
