"""Build the rail network from a GTFS feed and print a sanity report.

Usage:
    python scripts/inspect_network.py                         # LA Metro (data/raw/gtfs_rail.zip)
    python scripts/inspect_network.py --gtfs data/sample/gtfs # the made-up sample network

The report is how we check that real-world data turned into a sensible network:
how many stations and segments, which lines, whether everything is connected,
and whether any station appears twice (e.g. one transfer station split into two nodes).
"""

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metro.gtfs import load_network  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanity report for a GTFS rail network.")
    parser.add_argument("--gtfs", type=Path, default=ROOT / "data" / "raw" / "gtfs_rail.zip")
    args = parser.parse_args()

    if not args.gtfs.exists():
        print(f"{args.gtfs} not found. Run first: python scripts/fetch_gtfs.py")
        return 1

    start = time.perf_counter()
    G = load_network(args.gtfs)
    seconds = time.perf_counter() - start

    lines = sorted({line for _, _, routes in G.edges(data="routes") for line in routes})
    components = list(nx.connected_components(G))
    times = [w for _, _, w in G.edges(data="weight")]

    print(f"Built from {args.gtfs.name} in {seconds:.2f} s")
    print(f"  Stations: {G.number_of_nodes()}")
    print(f"  Segments: {G.number_of_edges()}")
    print(f"  Lines:    {', '.join(lines)}")
    print(f"  Connected pieces: {len(components)} (1 means every station can reach every other)")
    if times:
        print(f"  Segment times: {min(times):g} to {max(times):g} min")

    print("\nBusiest junctions (most connections):")
    for station in sorted(G, key=lambda s: -G.degree(s))[:8]:
        print(f"  {G.nodes[station]['name']} ({G.degree(station)} connections)")

    # Possible problems to look at by hand ------------------------------------------------
    by_name = defaultdict(list)
    for station, name in G.nodes(data="name"):
        by_name[name].append(station)
    duplicates = {name: ids for name, ids in by_name.items() if len(ids) > 1}

    print("\nChecks:")
    print(f"  Same name on more than one node: {len(duplicates) or 'none'}")
    for name, ids in sorted(duplicates.items()):
        print(f"    {name}: {', '.join(ids)}")
    if len(components) > 1:
        print("  Stations NOT in the main network:")
        for piece in sorted(components, key=len)[:-1]:
            print(f"    {', '.join(sorted(G.nodes[s]['name'] for s in piece))}")
    missing_coords = [s for s, lat in G.nodes(data="lat") if lat is None]
    print(f"  Stations missing coordinates: {len(missing_coords) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
