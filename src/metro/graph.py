"""Building the rail network as a NetworkX graph.

The network is a plain undirected `networkx.Graph`:
- Nodes are stations, keyed by station_id, with attributes: name, lat, lon (and later ridership).
      G.add_node("A", name="Alder", lat=34.05, lon=-118.30)
- Edges are rail segments with attributes:
      weight = travel time in minutes (NetworkX algorithms read the "weight" attribute)
      routes = set of line names that run on this segment, e.g. {"A Line", "E Line"}

This file holds only the two rules NetworkX doesn't know about our transit data.
"""

from __future__ import annotations

from typing import Iterable, Optional

import networkx as nx


def add_segment(G: nx.Graph, u: str, v: str, minutes: float, route: Optional[str] = None) -> None:
    """Add a rail segment between stations u and v.

    If two lines run between the same pair of stations, keep the FASTER time (a rider
    would take the faster one) and remember every line name that uses the segment.
    """
    if u == v:
        raise ValueError(f"a station can't connect to itself: {u!r}")
    if minutes < 0:
        raise ValueError(f"travel time can't be negative: {u!r}-{v!r} = {minutes}")
    if G.has_edge(u, v):
        G[u][v]["weight"] = min(G[u][v]["weight"], minutes)
    else:
        G.add_edge(u, v, weight=minutes, routes=set())
    if route is not None:
        G[u][v]["routes"].add(route)


def close_stations(G: nx.Graph, closed: Iterable[str]) -> nx.Graph:
    """A COPY of the network with the closed stations (and their segments) removed.

    The original is never changed, so the app can try many closures in a row.
    """
    H = G.copy()
    H.remove_nodes_from(closed)
    return H
