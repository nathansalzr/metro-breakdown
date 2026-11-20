import networkx as nx

from metro.graph import add_segment
from metro.rerouting import find_route, reroute

def make_test_graph():
    # Create a small network to test our routes
    G = nx.Graph()

    # Connect stations and give each connection a travel time
    add_segment(G, "A", "B", 3)
    add_segment(G, "B", "C", 4)
    add_segment(G, "C", "D", 3)

    # Add another route that avoids station B
    add_segment(G, "A", "E", 5)
    add_segment(G, "E", "D", 8)

    return G


def test_normal_route():
    # Check that the fastest route is found
    G = make_test_graph()

    path, time = find_route(G, "A", "D")

    assert path == ["A", "B", "C", "D"]
    assert time == 10


def test_station_closure():
    # Close station B and check the new route
    G = make_test_graph()

    result = reroute(G, "A", "D", ["B"])

    assert result["original"][0] == ["A", "B", "C", "D"]
    assert result["alternative"][0] == ["A", "E", "D"]
    assert result["extra_minutes"] == 3

    # Make sure the original graph was not changed
    assert "B" in G


def test_no_alternative():
    # Close both possible routes
    G = make_test_graph()

    result = reroute(G, "A", "D", ["B", "E"])

    assert result["alternative"] is None
    assert result["extra_minutes"] is None


def test_invalid_station():
    # Check what happens if a station does not exist
    G = make_test_graph()

    assert find_route(G, "A", "Z") is None
