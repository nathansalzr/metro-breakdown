"""US-4: stress-test the network by closing stations one after another.

CECS 427 concept: network robustness. We close k stations one at a time and, after each
closure, measure how much of the network still hangs together: the share of the original
stations that are in the largest connected piece. Plotting that share against the number of
closures gives a "breakdown curve".

Three ways to pick the next station to close:
- "random": random failures, like unrelated breakdowns. Averaged over 20 runs.
- "degree": the station with the most connections (neighbors) right now.
- "betweenness": the station that the most fastest routes pass through right now.

"degree" and "betweenness" model a targeted disruption of the hubs. They are recomputed after
every closure, because once a hub is gone, the routes (and the next most important station)
change. Real networks often survive random failures well but fall apart quickly when the
hubs are targeted; the curves show whether LA Metro does.

Stations are station IDs, the same as in rerouting.py and centrality.py.
"""

from __future__ import annotations

import random
from typing import List

import networkx as nx

from .centrality import top_stations

STRATEGIES = ("random", "degree", "betweenness")
RANDOM_RUNS = 20


def breakdown_curve(G: nx.Graph, k: int, strategy: str, seed: int = 0) -> List[float]:
    """Share of stations still in the largest connected piece after 0, 1, ..., k closures.

    Returns k + 1 numbers between 0 and 1. The first is 1.0 for a connected network.
    The share is out of the ORIGINAL number of stations, so closed stations count as lost.
    For "random", the curve is the average of 20 random closure orders made from `seed`,
    so the same seed always gives the same curve. The original network is not changed.

    Uses nx.connected_components to find the pieces after each closure.
    """
    _check(G, k, strategy)
    if strategy == "random":
        rng = random.Random(seed)
        stations = sorted(G.nodes())
        runs = [_curve(G, rng.sample(stations, k)) for _ in range(RANDOM_RUNS)]
        return [sum(values) / RANDOM_RUNS for values in zip(*runs)]
    return _curve(G, removal_order(G, k, strategy))


def removal_order(G: nx.Graph, k: int, strategy: str) -> List[str]:
    """The k stations a targeted strategy closes, in order ("degree" or "betweenness").

    After each closure the next station is picked again on what is left of the network.
    "degree" uses G.degree (number of neighbors); "betweenness" uses top_stations from
    centrality.py (nx.betweenness_centrality, weighted by travel time). Ties go to the
    station whose name comes first, so the order is always the same.
    """
    _check(G, k, strategy)
    if strategy == "random":
        raise ValueError('"random" has no fixed order; use breakdown_curve with a seed')

    H = G.copy()
    order = []
    for _ in range(k):
        if strategy == "degree":
            target = min(H.nodes(), key=lambda s: (-H.degree(s), H.nodes[s].get("name", s)))
        else:
            target = top_stations(H, 1)[0][0]
        order.append(target)
        H.remove_node(target)
    return order


def _curve(G: nx.Graph, order: List[str]) -> List[float]:
    """Largest-piece share before any closure and after each closure in `order`."""
    total = G.number_of_nodes()
    H = G.copy()
    shares = [_largest_share(H, total)]
    for station in order:
        H.remove_node(station)
        shares.append(_largest_share(H, total))
    return shares


def _largest_share(H: nx.Graph, total: int) -> float:
    if H.number_of_nodes() == 0:
        return 0.0
    return len(max(nx.connected_components(H), key=len)) / total


def _check(G: nx.Graph, k: int, strategy: str) -> None:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; use one of {', '.join(STRATEGIES)}")
    if not 0 <= k <= G.number_of_nodes():
        raise ValueError(f"k must be between 0 and {G.number_of_nodes()} (the number of stations), got {k}")
