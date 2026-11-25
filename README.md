# Metro Breakdown

**Measuring how LA Metro's rail network holds up when stations close.**

CECS 427 Dynamic Networks · California State University, Long Beach · Fall 2026

> **Status: in development.** The real LA Metro rail network loads. Rerouting around closed stations
> and critical-station analysis work and are tested. The app is next (see [Roadmap](#roadmap)).

---

## Overview

When a rail station closes because of an outage, an emergency, or maintenance, riders lose
their usual route, and parts of the network can be cut off entirely. Metro Breakdown models
LA Metro's rail system as a network and uses graph algorithms to show how a closure affects
riders and which stations the system depends on most.

### Questions it answers

| Audience | Question | Network method |
|----------|----------|----------------|
| Riders | *"My station is closed. What's my new route, and how much longer will it take?"* | Weighted shortest paths |
| Transit planners | *"Which stations are single points of failure?"* | Betweenness centrality, articulation points, bridges |
| Transit planners | *"Does the network survive random failures better than a targeted disruption of its hubs?"* | Connected components and breakdown curves |

## How the network is modeled

| Element | Represents | Details |
|---------|------------|---------|
| **Node** | A rail station | Name and location (latitude, longitude). Multi-line stations such as 7th St/Metro Center are a single node, so transfers are possible. |
| **Edge** | A rail segment between two consecutive stations | Weighted by scheduled travel time in minutes, and labeled with every line that uses it. |

The network is undirected (trains run both ways) and built with [NetworkX](https://networkx.org).
The data is LA Metro's public rail schedule in the standard [GTFS](https://gtfs.org/schedule/reference/) format.

## Getting started

**Requirements:** Python 3.9+ and Git, on Windows, macOS, or Linux. No accounts or API keys.

```bash
git clone https://github.com/nathansalzr/metro-breakdown.git
cd metro-breakdown
python -m venv .venv
```

Activate the virtual environment, then install the dependencies:

| Windows (PowerShell) | macOS / Linux |
|----------------------|---------------|
| `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |

```bash
pip install -r requirements-dev.txt
```

Run the tests (all should pass):

```bash
python -m pytest -v
```

## Development phases

Each phase builds on the one before it. Run them in order to follow how the project was built.

### Phase 1: Network foundation

The network is a NetworkX graph. `src/metro/graph.py` adds two transit-specific rules:

- `add_segment(G, u, v, minutes, route)` connects two stations. When several lines share a segment, it keeps the fastest time and records every line.
- `close_stations(G, closed)` returns a copy of the network without the given stations, leaving the original unchanged.

**Try it** (from the project folder, in `python`):

```python
import sys; sys.path.insert(0, "src")
import networkx as nx
from metro.graph import add_segment, close_stations

G = nx.Graph()
add_segment(G, "A", "B", 3, route="Red")
add_segment(G, "B", "C", 4, route="Red")
add_segment(G, "C", "D", 2, route="Red")
add_segment(G, "B", "E", 5, route="Blue")

nx.shortest_path(G, "A", "E", weight="weight")   # ['A', 'B', 'E']
sorted(nx.articulation_points(G))                # single points of failure: ['B', 'C']
list(nx.connected_components(close_stations(G, ["B"])))  # closing B splits the network in 3
```

Tests: `tests/test_graph.py`

### Phase 2: Load LA Metro's schedule

`src/metro/gtfs.py` turns a GTFS schedule into the network with `load_network(path)`:

- Keeps rail lines only (light rail and subway); buses are dropped.
- Merges each station's platforms into one node.
- Builds a segment from each pair of consecutive stops; its weight is the median travel time in minutes.

`data/sample/gtfs/` is a made-up 10-station network used to test those rules
(`tests/test_gtfs.py`). Each rule has a matching test.

**Load the real network:**

```bash
python scripts/fetch_gtfs.py        # downloads LA Metro's rail schedule (~1.6 MB) to data/raw/
python scripts/inspect_network.py   # builds the network and prints a sanity report
```

Expected: about 111 stations, 112 segments, 6 lines (A, B, C, D, E, K), 1 connected piece, and
no duplicate stations. Run `python scripts/inspect_network.py --gtfs data/sample/gtfs` to see the
same report for the sample network.

### Phase 3: Trip planning and rerouting

`src/metro/rerouting.py` answers the rider's question with NetworkX's weighted shortest path:

- `find_route(G, start, end)` returns the fastest route and its minutes, or `None` if there is no route.
- `reroute(G, start, end, closed)` compares the normal route with the route after closing stations and reports the added minutes, or `None` when the trip becomes impossible.

**Try it** (sample network, in `python`):

```python
import sys; sys.path.insert(0, "src")
from metro.gtfs import load_network
from metro.rerouting import reroute

G = load_network("data/sample/gtfs")
reroute(G, "A", "G", ["C"])   # closing Cedar Junction: 10 -> 13 minutes, +3
```

Tests: `tests/test_rerouting.py`. The app screen for this phase is still to come.

### Phase 4: Critical stations

`src/metro/centrality.py` answers the planner's question:

- `top_stations(G, k)` ranks stations by betweenness centrality: how many fastest routes pass through each one.
- `single_points_of_failure(G)` lists the stations (articulation points) and segments (bridges) whose closure splits the network.
- `pieces_after_closing(G, station)` shows the separate pieces left after closing one station, largest first.

**Try it** (sample network, in `python`):

```python
import sys; sys.path.insert(0, "src")
from metro.gtfs import load_network
from metro.centrality import top_stations, pieces_after_closing

G = load_network("data/sample/gtfs")
top_stations(G, 3, normalized=False)   # Cedar Junction 20, Birch 14, Ginkgo 14
pieces_after_closing(G, "C")           # Fir is cut off from the other 8 stations
```

On LA data the top 3 are Pico, 7th St/Metro Center, and Willowbrook/Rosa Parks.
95 of 111 stations are single points of failure (articulation points), and 100 of 112 segments
are bridges. Tests: `tests/test_centrality.py`.

**Team guide:** [docs/ROADMAP.md](docs/ROADMAP.md) walks through every use case: what it does, the files,
the steps, and how we know it's done.

## Project structure

```
metro-breakdown/
├── src/metro/
│   ├── graph.py            Phase 1: add_segment, close_stations
│   ├── gtfs.py             Phase 2: load_network (GTFS schedule -> network)
│   ├── rerouting.py        Phase 3: find_route, reroute
│   └── centrality.py       Phase 4: top_stations, single_points_of_failure, pieces_after_closing
├── scripts/
│   ├── fetch_gtfs.py       Download LA Metro's rail schedule
│   └── inspect_network.py  Sanity report for a loaded network
├── data/sample/gtfs/       Made-up 10-station network for tests
├── docs/ROADMAP.md         Use-case walkthrough for the team
├── CITATIONS.md            Data, libraries, references, AI assistance
├── tests/                  One test file per module
├── requirements.txt        Libraries the app needs
├── requirements-dev.txt    Plus testing tools
└── pyproject.toml          Project and test settings
```

`data/raw/` (the downloaded LA schedule) is not committed; `fetch_gtfs.py` recreates it.

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Network foundation | Complete |
| 2 | Load LA Metro's rail schedule | Complete |
| 3 | Trip planning and rerouting around closed stations | In progress (logic done, app screen next) |
| 4 | Critical-station analysis (centrality, single points of failure) | In progress (logic done, app screen next) |
| 5 | Resilience experiments: random vs. targeted closures | Planned |
| 6 | Interactive web app with a map | Planned |

## Technology

| Purpose | Tool |
|---------|------|
| Language | Python 3.9+ |
| Network modeling and algorithms | NetworkX |
| Testing | pytest |

## Team

Each member presents the part they built. Roles match [docs/ROADMAP.md](docs/ROADMAP.md#2-who-owns-what).

| Name | Role | Contributions |
|------|------|---------------|
| Nathan Salazar | Project manager | Network foundation (`graph.py`), GTFS loader (`gtfs.py`) and data scripts, reviews and merges, US-2 acceptance tests, ROADMAP and README |
| Paula Awad | R2 Routing | Trip planning and rerouting (`rerouting.py`, US-2) |
| *TBD* | R1 Data | |
| *TBD* | R3 Centrality | |
| *TBD* | R4 Resilience | |
| *TBD* | R5 App | |
| *TBD* | R6 QA and Docs | |

## Acknowledgments

Full list of data, libraries, references, and AI assistance: [CITATIONS.md](CITATIONS.md).

- **LA Metro** for publishing its rail schedule as open data ([gitlab.com/LACMTA/gtfs_rail](https://gitlab.com/LACMTA/gtfs_rail)).
- **NetworkX** (BSD-3 license) for graph modeling and algorithms.
- Developed for **CECS 427 Dynamic Networks**, taught by Prof. Kate Nguyen at California State University, Long Beach.
