"""Metro Breakdown web app.

Run from the project folder:  streamlit run app.py

Tabs:
- Trip planner (US-1, US-2): fastest route, and the detour or "Unreachable" when stations close.
- Critical stations (US-3): busiest stations, single points of failure, and what one closure splits.
- Stress test (US-4): random failures vs. targeted attacks on the hubs, as breakdown curves.

The app only shows results. All network logic lives in src/metro/ and has its own tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Optional

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from metro.centrality import pieces_after_closing, single_points_of_failure, top_stations  # noqa: E402
from metro.gtfs import load_network  # noqa: E402
from metro.resilience import breakdown_curve, removal_order  # noqa: E402
from metro.rerouting import reroute  # noqa: E402

SOURCES = {
    "LA Metro rail": ROOT / "data" / "raw" / "gtfs_rail.zip",
    "Sample network": ROOT / "data" / "sample" / "gtfs",
}
# Default trip for each network: the demo trip on LA, Alder -> Ginkgo on the sample.
DEFAULT_TRIP = {
    "LA Metro rail": ("Downtown Long Beach", "Union Station"),
    "Sample network": ("Alder", "Ginkgo"),
}


@st.cache_resource(show_spinner="Loading the network...")
def get_network(path: str) -> nx.Graph:
    """Load a network once and reuse it on every click (loading LA data takes a moment)."""
    return load_network(path)


def minutes_text(minutes: float) -> str:
    """Minutes for display: "62 min", or "40.5 min" when a trip ends in a half minute.

    Some LA segments take 1.5 or 2.5 minutes. Showing the half keeps the numbers adding up
    (40.5 + 3 = 43.5); rounding each one on its own could show 40 + 3 = 44.
    """
    minutes = round(minutes, 1)
    return f"{minutes:.0f} min" if minutes == int(minutes) else f"{minutes:.1f} min"


def name(G: nx.Graph, station: str) -> str:
    return G.nodes[station].get("name", station)


def find_station(G: nx.Graph, options: List[str], text: str) -> int:
    """Index of the first station whose name contains text, or 0 if none does."""
    for i, station in enumerate(options):
        if text.lower() in name(G, station).lower():
            return i
    return 0


@st.cache_resource(show_spinner="Finding the critical stations...")
def get_critical(path: str) -> tuple:
    """Every station ranked by betweenness, plus the single points of failure (computed once)."""
    G = get_network(path)
    return top_stations(G, G.number_of_nodes()), single_points_of_failure(G)


# One color per piece after a closure, largest piece first.
PIECE_COLORS = ["#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f"]


def base_map(G: nx.Graph, show_stations: bool = True) -> go.Figure:
    """Map with every rail segment in grey, and (optionally) every station."""
    fig = go.Figure()

    # All segments in one grey trace. None between segments lifts the pen.
    lats, lons = [], []
    for u, v in G.edges():
        lats += [G.nodes[u]["lat"], G.nodes[v]["lat"], None]
        lons += [G.nodes[u]["lon"], G.nodes[v]["lon"], None]
    fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", line=dict(width=2, color="#b0b0b0"),
                                hoverinfo="skip", name="Rail segments"))

    if show_stations:
        stations = list(G.nodes())
        fig.add_trace(go.Scattermap(
            lat=[G.nodes[s]["lat"] for s in stations], lon=[G.nodes[s]["lon"] for s in stations],
            mode="markers", marker=dict(size=7, color="#707070"),
            text=[name(G, s) for s in stations], hoverinfo="text", name="Stations",
        ))
    return fig


def add_closed(fig: go.Figure, G: nx.Graph, closed: Iterable[str]) -> None:
    closed = list(closed)
    if closed:
        fig.add_trace(go.Scattermap(
            lat=[G.nodes[s]["lat"] for s in closed], lon=[G.nodes[s]["lon"] for s in closed],
            mode="markers", marker=dict(size=14, color="#d62728"),
            text=[f"{name(G, s)} (closed)" for s in closed], hoverinfo="text", name="Closed",
        ))


def finish_map(fig: go.Figure, G: nx.Graph) -> go.Figure:
    """Center and zoom the map on the whole network, and make the legend readable."""
    all_lats = [G.nodes[s]["lat"] for s in G.nodes()]
    all_lons = [G.nodes[s]["lon"] for s in G.nodes()]
    span = max(max(all_lats) - min(all_lats), max(all_lons) - min(all_lons))
    fig.update_layout(
        map=dict(
            style="open-street-map",
            # Center on the middle of the network so the whole system fits.
            center=dict(lat=(min(all_lats) + max(all_lats)) / 2, lon=(min(all_lons) + max(all_lons)) / 2),
            zoom=9.2 if span > 0.3 else 12,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=550,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)", font=dict(color="#222222")),
    )
    return fig


def route_map(
    G: nx.Graph,
    route: Optional[List[str]] = None,
    detour: Optional[List[str]] = None,
    closed: Iterable[str] = (),
) -> go.Figure:
    """Map of every segment and station, with the route, detour and closed stations on top."""
    fig = base_map(G)
    for path, color, label, width in [(route, "#1f77b4", "Normal route", 9), (detour, "#ff7f0e", "Detour", 4)]:
        if path:
            fig.add_trace(go.Scattermap(
                lat=[G.nodes[s]["lat"] for s in path], lon=[G.nodes[s]["lon"] for s in path],
                # The normal route is drawn wider so it still shows under the detour.
                mode="lines+markers", line=dict(width=width, color=color), marker=dict(size=width + 4, color=color),
                text=[name(G, s) for s in path], hoverinfo="text", name=label,
            ))

    add_closed(fig, G, closed)
    return finish_map(fig, G)


def pieces_map(G: nx.Graph, pieces: List[set], closed: str) -> go.Figure:
    """Map with each piece left after a closure in its own color, and the closed station in red."""
    fig = base_map(G, show_stations=False)
    for i, piece in enumerate(pieces):
        stations = sorted(piece)
        fig.add_trace(go.Scattermap(
            lat=[G.nodes[s]["lat"] for s in stations], lon=[G.nodes[s]["lon"] for s in stations],
            mode="markers", marker=dict(size=9, color=PIECE_COLORS[i % len(PIECE_COLORS)]),
            text=[name(G, s) for s in stations], hoverinfo="text",
            name=f"Piece {i + 1} ({len(piece)} station{'' if len(piece) == 1 else 's'})",
        ))
    add_closed(fig, G, [closed])
    return finish_map(fig, G)


def trip_planner(G: nx.Graph, source: str) -> None:
    key = "sample" if source == "Sample network" else "la"
    options = sorted(G.nodes(), key=lambda s: name(G, s))
    start_text, end_text = DEFAULT_TRIP[source]

    col1, col2 = st.columns(2)
    start = col1.selectbox("From", options, index=find_station(G, options, start_text),
                           format_func=lambda s: name(G, s), key=f"start_{key}")
    end = col2.selectbox("To", options, index=find_station(G, options, end_text),
                         format_func=lambda s: name(G, s), key=f"end_{key}")
    closed = st.multiselect("Closed stations", options, format_func=lambda s: name(G, s),
                            key=f"closed_{key}")

    if start == end:
        st.info("Pick two different stations.")
        st.plotly_chart(route_map(G, closed=closed), width="stretch")
        return

    result = reroute(G, start, end, closed)
    original, alternative = result["original"], result["alternative"]

    if original is None:
        st.error("These stations aren't connected, even with nothing closed.")
        return

    route, minutes = original
    detour = None
    if not closed:
        st.metric("Fastest route", minutes_text(minutes))
    else:
        col1, col2 = st.columns(2)
        col1.metric("Normal route", minutes_text(minutes))
        if alternative is None:
            st.error(
                f"Unreachable: with {', '.join(name(G, s) for s in closed)} closed, there is no way "
                f"from {name(G, start)} to {name(G, end)}. The closure cuts this trip off."
            )
        else:
            detour, new_minutes = alternative
            extra = result["extra_minutes"]
            if round(extra, 1) == 0:
                # The closure isn't on this route, so the trip takes the same time: no red arrow.
                col2.metric("With closures", minutes_text(new_minutes), delta="No change", delta_color="off")
            else:
                col2.metric("With closures", minutes_text(new_minutes),
                            delta="+" + minutes_text(extra), delta_color="inverse")

    st.write("**Normal route:** " + " > ".join(name(G, s) for s in route))
    if detour:
        st.write("**Detour:** " + " > ".join(name(G, s) for s in detour))
    st.plotly_chart(route_map(G, route=route, detour=detour, closed=closed), width="stretch")


def critical_stations(G: nx.Graph, source: str) -> None:
    key = "sample" if source == "Sample network" else "la"
    ranked, spof = get_critical(str(SOURCES[source]))
    n = G.number_of_nodes()

    st.subheader("Busiest stations")
    st.caption("Betweenness centrality: the share of fastest routes between other stations "
               "that pass through each station.")
    k = st.slider("How many stations", 1, min(20, n), min(10, n), key=f"k_{key}")
    st.dataframe(
        [{"Rank": i + 1, "Station": station_name, "Share of fastest routes": f"{score:.1%}"}
         for i, (_, station_name, score) in enumerate(ranked[:k])],
        hide_index=True,
    )

    st.subheader("Single points of failure")
    st.caption("Closing any one of these splits the network, so some riders can no longer "
               "reach some stations at all.")
    col1, col2 = st.columns(2)
    col1.metric("Stations (articulation points)", f"{len(spof['stations'])} of {n}")
    col2.metric("Segments (bridges)", f"{len(spof['segments'])} of {G.number_of_edges()}")
    with st.expander("List the stations"):
        st.write(", ".join(sorted(name(G, s) for s in spof["stations"])) or "None")

    st.subheader("Close one station")
    options = sorted(G.nodes(), key=lambda s: name(G, s))
    busiest = ranked[0][0]
    closed = st.selectbox("Station to close", options, index=options.index(busiest),
                          format_func=lambda s: name(G, s), key=f"close_{key}")
    pieces = pieces_after_closing(G, closed)
    counts = [str(len(p)) for p in pieces]
    sizes = counts[0] if len(counts) == 1 else ", ".join(counts[:-1]) + " and " + counts[-1]
    if len(pieces) == 1:
        st.success(f"Closing {name(G, closed)} leaves the network in one piece ({sizes} stations).")
    else:
        st.warning(f"Closing {name(G, closed)} splits the network into {len(pieces)} pieces: "
                   f"{sizes} stations. Riders can't travel between pieces.")
    st.plotly_chart(pieces_map(G, pieces, closed), width="stretch")


# Label and color for each strategy on the chart.
STRESS_LINES = [
    ("random", "Random failures", "Random failures (average of 20 runs)", "#7f7f7f"),
    ("degree", "Most connections first", "Targeted: most connections first", "#ff7f0e"),
    ("betweenness", "Busiest stations first", "Targeted: busiest stations first", "#d62728"),
]


@st.cache_data(show_spinner="Running the stress test...")
def get_curve(path: str, k: int, strategy: str, seed: int) -> List[float]:
    """Breakdown curve for one strategy (cached, so switching tabs doesn't recompute it)."""
    return breakdown_curve(get_network(path), k, strategy, seed=seed)


def stress_test(G: nx.Graph, source: str) -> None:
    key = "sample" if source == "Sample network" else "la"
    path = str(SOURCES[source])
    n = G.number_of_nodes()

    st.caption("Close stations one at a time and watch how much of the network still hangs "
               "together: the share of all stations in the largest connected piece.")
    col1, col2 = st.columns(2)
    k = col1.slider("Stations to close", 1, min(30, n), min(10, n // 2), key=f"kstress_{key}")
    seed = int(col2.number_input("Random seed", 0, 9999, 0, key=f"seed_{key}",
                                 help="The same seed always gives the same random curve."))

    curves = {strategy: get_curve(path, k, strategy, seed) for strategy, _, _, _ in STRESS_LINES}

    st.write(f"**Stations still in the largest piece after {k} closures:**")
    cols = st.columns(3)
    for col, (strategy, short, _, _) in zip(cols, STRESS_LINES):
        col.metric(short, f"{curves[strategy][-1]:.0%}")

    fig = go.Figure()
    for strategy, _, label, color in STRESS_LINES:
        fig.add_trace(go.Scatter(
            x=list(range(k + 1)), y=[share * 100 for share in curves[strategy]],
            mode="lines+markers", name=label, line=dict(color=color, width=3),
        ))
    fig.update_layout(
        xaxis_title="Stations closed", yaxis_title="Stations in the largest piece (%)",
        yaxis=dict(range=[0, 105]), height=450, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(x=0.99, y=0.99, xanchor="right", bgcolor="rgba(255,255,255,0.85)",
                    font=dict(color="#222222")),
    )
    st.plotly_chart(fig, width="stretch")

    with st.expander("Which stations the targeted attacks close"):
        for strategy, _, label, _ in STRESS_LINES[1:]:
            order = removal_order(G, k, strategy)
            st.write(f"**{label}:** " + " > ".join(name(G, s) for s in order))


def main() -> None:
    st.set_page_config(page_title="Metro Breakdown", layout="wide")
    st.title("Metro Breakdown")
    st.caption("How LA Metro's rail network holds up when stations close. CECS 427, CSULB.")

    la_ready = SOURCES["LA Metro rail"].exists()
    source = st.sidebar.radio("Network", list(SOURCES), index=0 if la_ready else 1, key="source")
    if source == "LA Metro rail" and not la_ready:
        st.sidebar.warning("LA data not downloaded yet. Run `python scripts/fetch_gtfs.py`, "
                           "then refresh. Showing the sample network for now.")
        source = "Sample network"
    G = get_network(str(SOURCES[source]))
    st.sidebar.write(f"{G.number_of_nodes()} stations, {G.number_of_edges()} segments")

    trips, critical, stress = st.tabs(["Trip planner", "Critical stations", "Stress test"])
    with trips:
        trip_planner(G, source)
    with critical:
        critical_stations(G, source)
    with stress:
        stress_test(G, source)


if __name__ == "__main__":  # streamlit run sets this; lets tests import minutes_text
    main()
