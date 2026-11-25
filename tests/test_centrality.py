from pathlib import Path

import networkx as nx
import pytest

from metro.graph import add_segment
from metro.centrality import pieces_after_closing, single_points_of_failure, top_stations
from metro.gtfs import load_network

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample" / "gtfs"


@pytest.fixture
def sample():
    return load_network(SAMPLE)


# --- top_stations: betweenness centrality -------------------------------------------------

def test_top_stations_match_answer_key(sample):
    # Answer key (docs/ROADMAP.md, UC-3): Cedar Junction 20, Birch 14, Ginkgo 14,
    # then Alder, Dogwood, Hawthorn 8 each. Ties are broken by name.
    top = top_stations(sample, 6, normalized=False)
    assert top == [
        ("C", "Cedar Junction", 20),
        ("B", "Birch", 14),
        ("G", "Ginkgo", 14),
        ("A", "Alder", 8),
        ("D", "Dogwood", 8),
        ("H", "Hawthorn", 8),
    ]


def test_top_stations_returns_only_k(sample):
    assert [sid for sid, _, _ in top_stations(sample, 3)] == ["C", "B", "G"]


def test_top_stations_default_scores_are_normalized(sample):
    # Normalized scores are shares between 0 and 1, so LA and sample results compare fairly.
    scores = [score for _, _, score in top_stations(sample, 10)]
    assert all(0 <= s <= 1 for s in scores)


def test_top_stations_rejects_bad_k(sample):
    with pytest.raises(ValueError):
        top_stations(sample, 0)


# --- single_points_of_failure: articulation points and bridges ----------------------------

def test_single_points_of_failure_match_answer_key(sample):
    result = single_points_of_failure(sample)
    assert result["stations"] == ["A", "B", "C", "D", "G", "H"]
    assert result["segments"] == [
        ("A", "B"), ("A", "J"), ("C", "F"), ("D", "E"), ("G", "H"), ("H", "I"),
    ]


def test_a_loop_has_no_single_points_of_failure():
    # In a loop, every station has two ways around, so no closure splits the network.
    G = nx.Graph()
    for u, v in [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")]:
        add_segment(G, u, v, 2)
    assert single_points_of_failure(G) == {"stations": [], "segments": []}


# --- pieces_after_closing: connected components ------------------------------------------

def test_closing_a_single_point_of_failure_splits_the_network(sample):
    # Cedar Junction is the only link to Fir.
    pieces = pieces_after_closing(sample, "C")
    assert pieces == [{"A", "B", "D", "E", "G", "H", "I", "J"}, {"F"}]


def test_closing_a_normal_station_keeps_one_piece(sample):
    # Elm is an end station, so the other 9 stay connected.
    pieces = pieces_after_closing(sample, "E")
    assert len(pieces) == 1 and len(pieces[0]) == 9


def test_pieces_after_closing_leaves_original_unchanged(sample):
    pieces_after_closing(sample, "C")
    assert "C" in sample and sample.number_of_nodes() == 10


def test_pieces_after_closing_rejects_unknown_station(sample):
    with pytest.raises(ValueError):
        pieces_after_closing(sample, "Cedar Junction")  # a name, not an ID
