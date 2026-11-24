from pathlib import Path

import networkx as nx
import pytest

from metro.graph import add_segment
from metro.gtfs import load_network
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
    # A station that doesn't exist is an error, not "unreachable"
    G = make_test_graph()

    with pytest.raises(ValueError, match="Z"):
        find_route(G, "A", "Z")


# ----- Acceptance criteria on the sample network (data/sample/gtfs) -------------------
# Sample stations: A Alder, B Birch, C Cedar Junction, D Dogwood, G Ginkgo, I Ivy.
# Answer key: see the network drawing at the top of tests/test_gtfs.py.

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample" / "gtfs"


@pytest.fixture(scope="module")
def sample():
    return load_network(SAMPLE)


def test_ac1_closing_cedar_adds_three_minutes(sample):
    # US-2-AC1: Alder -> Ginkgo goes from 10 to 13 minutes (+3) via A B D G
    result = reroute(sample, "A", "G", ["C"])

    assert result["original"] == (["A", "B", "C", "G"], 10)
    assert result["alternative"] == (["A", "B", "D", "G"], 13)
    assert result["extra_minutes"] == 3


def test_ac2_closing_ginkgo_makes_ivy_unreachable(sample):
    # US-2-AC2: no route left from Alder to Ivy
    result = reroute(sample, "A", "I", ["G"])

    assert result["original"][1] == 21
    assert result["alternative"] is None
    assert result["extra_minutes"] is None


def test_ac3_closing_the_origin_or_destination_is_unreachable(sample):
    # US-2-AC3: the rider's own start or end station is closed
    assert reroute(sample, "A", "G", ["A"])["alternative"] is None
    assert reroute(sample, "A", "G", ["G"])["alternative"] is None


# ----- Bad input is rejected instead of silently ignored --------------------------------


def test_unknown_closed_station_is_rejected(sample):
    # A typo or a station name (instead of its ID) must not quietly report "+0 minutes"
    with pytest.raises(ValueError, match="Cedar Junction"):
        reroute(sample, "A", "G", ["Cedar Junction"])


def test_single_string_instead_of_list_is_rejected(sample):
    with pytest.raises(ValueError, match="list"):
        reroute(sample, "A", "G", "C")
