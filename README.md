# Metro Breakdown

**Measuring how LA Metro's rail network holds up when stations close.**

CECS 427 Dynamic Networks · California State University, Long Beach · Fall 2026

> **Status: early development.** The network foundation is complete and tested. Data loading,
> the analyses, and the interactive app are in progress (see [Roadmap](#roadmap)).

---

## Overview

When a rail station closes because of an outage, an emergency, or maintenance, riders lose
their usual route, and parts of the network can be cut off entirely. Metro Breakdown models
LA Metro's rail system as a network and uses established graph algorithms to show how a
closure affects riders and which stations the system depends on most.

### Questions it answers

| Audience | Question | Network method |
|----------|----------|----------------|
| Riders | *"My station is closed. What's my new route, and how much longer will it take?"* | Weighted shortest paths |
| Transit planners | *"Which stations are single points of failure?"* | Betweenness centrality, articulation points, bridges |
| Transit planners | *"Does the network survive random failures better than a targeted disruption of its hubs?"* | Connected components and breakdown curves |

## How the network is modeled

| Element | Represents | Details |
|---------|------------|---------|
| **Node** | A rail station | Station name and location (latitude, longitude). Multi-line stations such as 7th St/Metro Center are a single node, so transfers are possible. |
| **Edge** | A rail segment between two consecutive stations | Weighted by scheduled travel time in minutes, and labeled with every line that uses it. |

The network is undirected (trains run both ways) and is built with
[NetworkX](https://networkx.org), the graph library used throughout CECS 427.

**Data source:** LA Metro's public rail schedule, published in the standard
[GTFS](https://gtfs.org/schedule/reference/) format.

## Getting started

### Requirements

- Python 3.9 or newer
- Git
- Windows, macOS, or Linux. No accounts, API keys, or database servers are required.

### Installation

```bash
git clone https://github.com/nathansalzr/metro-breakdown.git
cd metro-breakdown
python -m venv .venv
```

Activate the virtual environment:

| Windows (PowerShell) | macOS / Linux |
|----------------------|---------------|
| `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |

Install the dependencies:

```bash
pip install -r requirements-dev.txt
```

### Run the tests

```bash
python -m pytest -v
```

All tests should pass. They verify how the network is built: segment travel times, routes
shared by several lines, and station closures.

### Try it

Start Python from the project folder and build a small example network:

```python
import sys; sys.path.insert(0, "src")
import networkx as nx
from metro.graph import add_segment, close_stations

G = nx.Graph()
add_segment(G, "A", "B", 3, route="Red")
add_segment(G, "B", "C", 4, route="Red")
add_segment(G, "C", "D", 2, route="Red")
add_segment(G, "B", "E", 5, route="Blue")

nx.shortest_path(G, "A", "E", weight="weight")   # fastest route: ['A', 'B', 'E']
sorted(nx.articulation_points(G))                # single points of failure: ['B', 'C']

closed = close_stations(G, ["B"])                # what if station B closes?
list(nx.connected_components(closed))            # the network splits into 3 pieces
```

## Project structure

```
metro-breakdown/
├── src/metro/
│   └── graph.py          Network-building rules: add_segment, close_stations
├── tests/
│   └── test_graph.py     Tests for the network-building rules
├── requirements.txt      Libraries the app needs
├── requirements-dev.txt  Libraries the app needs, plus testing tools
├── pyproject.toml        Project and test settings
└── README.md
```

### Core functions

| Function | Purpose |
|----------|---------|
| `add_segment(G, u, v, minutes, route)` | Adds a rail segment. When several lines serve the same segment, it keeps the fastest travel time and records every line. |
| `close_stations(G, closed)` | Returns a copy of the network with the given stations removed, leaving the original unchanged so closures can be compared side by side. |

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Network foundation and tests | ✅ Complete |
| 2 | Load LA Metro's rail schedule (GTFS) into the network | ⏳ Next |
| 3 | Trip planning and rerouting around closed stations | Planned |
| 4 | Critical-station analysis (centrality, single points of failure) | Planned |
| 5 | Resilience experiments: random vs. targeted closures | Planned |
| 6 | Interactive web app with a map of the network | Planned |

## Technology

| Purpose | Tool |
|---------|------|
| Language | Python 3.9+ |
| Network modeling and algorithms | NetworkX |
| Testing | pytest |

## Team

| Name | Role |
|------|------|
| Nathan Salazar | Project manager |
| *Team members to be added* | |

## Acknowledgments

- **LA Metro** for publishing its rail schedule as open data.
- **NetworkX** (BSD-3 license) for graph modeling and algorithms.
- Developed for **CECS 427 Dynamic Networks**, taught by Prof. Kate Nguyen at California State University, Long Beach.
