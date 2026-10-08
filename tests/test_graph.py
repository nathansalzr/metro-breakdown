"""Tests for the network-building rules in metro/graph.py. Run with:  python -m pytest"""

import networkx as nx
import pytest

from metro.graph import add_segment, close_stations


@pytest.fixture
def line():
    """A tiny line plus a branch:  A --3-- B --4-- C --2-- D,  and  B --5-- E."""
    G = nx.Graph()
    G.add_node("A", name="Alder", lat=34.05, lon=-118.30)
    add_segment(G, "A", "B", 3, route="Red")
    add_segment(G, "B", "C", 4, route="Red")
    add_segment(G, "C", "D", 2, route="Red")
    add_segment(G, "B", "E", 5, route="Blue")
    return G


def test_counts(line):
    assert line.number_of_nodes() == 5
    assert line.number_of_edges() == 4
    assert line.degree("B") == 3  # A, C, E


def test_edges_are_undirected(line):
    assert line["A"]["B"]["weight"] == line["B"]["A"]["weight"] == 3


def test_two_lines_on_one_segment_keep_the_faster_time(line):
    add_segment(line, "C", "B", 3, route="Gold")  # faster than Red's 4 minutes
    assert line["B"]["C"]["weight"] == 3
    assert line["B"]["C"]["routes"] == {"Red", "Gold"}
    assert line.number_of_edges() == 4  # still one segment, not two


def test_slower_line_does_not_overwrite_time(line):
    add_segment(line, "A", "B", 9, route="Express")
    assert line["A"]["B"]["weight"] == 3
    assert line["A"]["B"]["routes"] == {"Red", "Express"}


def test_rejects_impossible_segments():
    G = nx.Graph()
    with pytest.raises(ValueError):
        add_segment(G, "A", "A", 1)
    with pytest.raises(ValueError):
        add_segment(G, "A", "B", -1)


def test_station_details(line):
    assert line.nodes["A"]["name"] == "Alder"
    assert line.nodes["A"]["lat"] == 34.05


def test_networkx_uses_our_travel_times(line):
    # A -> D is A-B-C-D = 3 + 4 + 2 = 9 minutes
    assert nx.shortest_path(line, "A", "D", weight="weight") == ["A", "B", "C", "D"]
    assert nx.shortest_path_length(line, "A", "D", weight="weight") == 9


def test_close_stations_removes_station_and_its_segments(line):
    closed = close_stations(line, ["B"])
    assert "B" not in closed
    assert closed.number_of_nodes() == 4
    assert closed.number_of_edges() == 1  # only C-D survives
    assert closed.degree("A") == 0
    assert not nx.has_path(closed, "A", "D")


def test_close_stations_leaves_the_original_alone(line):
    close_stations(line, ["B"])
    assert "B" in line
    assert line.number_of_edges() == 4
