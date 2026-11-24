"""Tests for metro/gtfs.py using the made-up sample feed in data/sample/gtfs.

Expected network (10 stations, 11 segments, minutes on each segment):

 Juniper(J)                    Fir(F)
    | 3 Green                    | 4 Blue
 Alder(A) -3- Birch(B) -4- Cedar Junction(C) -3- Ginkgo(G) -6- Hawthorn(H) -5- Ivy(I)
                |   Red          | 2 Red          |   Blue
                +--6 Gold-- Dogwood(D) --4 Gold---+
                                | 5 Red
                              Elm(E)
"""

import shutil
from pathlib import Path

import networkx as nx
import pytest

from metro.gtfs import load_network

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample" / "gtfs"


@pytest.fixture(scope="module")
def G():
    return load_network(SAMPLE)


def test_size(G):
    assert G.number_of_nodes() == 10
    assert G.number_of_edges() == 11


def test_buses_are_dropped(G):
    # Bus 9 runs Alder -> Elm directly; that must not become a rail segment.
    assert not G.has_edge("A", "E")


def test_platforms_merge_into_one_station(G):
    assert "C" in G
    assert "C1" not in G and "C2" not in G
    assert G.nodes["C"]["name"] == "Cedar Junction"
    # Red (platform C1) and Blue (platform C2) now meet at the same node, so riders can transfer.
    assert G["B"]["C"]["routes"] == {"Red"} and G["C"]["G"]["routes"] == {"Blue"}


def test_weight_is_the_median_time(G):
    # Birch -> Cedar was observed as 4, 6, and 4 minutes.
    assert G["B"]["C"]["weight"] == 4


def test_waiting_at_a_platform_is_not_riding_time(G):
    # Trip R1 arrives at Cedar 8:07, leaves 8:08, reaches Dogwood 8:10: 2 minutes, not 3.
    assert G["C"]["D"]["weight"] == 2


def test_both_directions_count_as_one_segment(G):
    # R2 runs Elm -> Alder, R1/R3 run Alder -> Elm; still one D-E segment.
    assert G["D"]["E"]["weight"] == 5
    assert G["D"]["E"]["routes"] == {"Red"}


def test_station_details(G):
    assert G.nodes["A"]["name"] == "Alder"
    assert G.nodes["A"]["lat"] == pytest.approx(34.05)
    assert G.nodes["A"]["lon"] == pytest.approx(-118.30)


def test_fastest_route_on_the_built_network(G):
    assert nx.shortest_path(G, "A", "I", weight="weight") == ["A", "B", "C", "G", "H", "I"]
    assert nx.shortest_path_length(G, "A", "I", weight="weight") == 21


def test_reads_a_zip_file_too(tmp_path):
    # Real feeds (like LA Metro's) come as a .zip.
    zipped = shutil.make_archive(str(tmp_path / "sample"), "zip", SAMPLE)
    G = load_network(zipped)
    assert G.number_of_nodes() == 10 and G.number_of_edges() == 11


def test_missing_file_gives_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="routes.txt"):
        load_network(tmp_path)
