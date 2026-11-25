import itertools
from pathlib import Path

import networkx as nx
import pytest

from metro.graph import add_segment
from metro.gtfs import load_network
from metro.resilience import STRATEGIES, breakdown_curve, removal_order

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample" / "gtfs"
LA = ROOT / "data" / "raw" / "gtfs_rail.zip"


@pytest.fixture
def sample():
    return load_network(SAMPLE)


# --- Done when (docs/ROADMAP.md, UC-4) ----------------------------------------------------

@pytest.mark.parametrize("strategy", STRATEGIES)
def test_curve_has_k_plus_1_points_and_starts_at_1(sample, strategy):
    curve = breakdown_curve(sample, 5, strategy)
    assert len(curve) == 6
    assert curve[0] == 1.0


def test_same_seed_gives_the_same_random_curve(sample):
    assert breakdown_curve(sample, 5, "random", seed=7) == breakdown_curve(sample, 5, "random", seed=7)


@pytest.mark.skipif(not LA.exists(), reason="LA data not downloaded (run scripts/fetch_gtfs.py)")
def test_on_la_data_the_targeted_attack_drops_faster_than_random():
    G = load_network(LA)
    targeted = breakdown_curve(G, 10, "betweenness")
    random_failures = breakdown_curve(G, 10, "random", seed=0)
    assert targeted[-1] < random_failures[-1]
    # The two targeted strategies give different curves on LA (22% vs 9% after 10 closures).
    assert breakdown_curve(G, 10, "degree") != targeted


# --- How each strategy behaves on the sample network ---------------------------------------

def test_targeted_strategies_remove_cedar_junction_first(sample):
    # Cedar Junction has the most connections (4, tied with Dogwood; ties go by name)
    # and the highest betweenness (20).
    assert removal_order(sample, 1, "degree") == ["C"]
    assert removal_order(sample, 1, "betweenness") == ["C"]


def test_degree_and_betweenness_can_pick_different_stations():
    # On the sample network both strategies happen to pick the same order, so this made-up
    # network makes sure they really differ. A is in a tight cluster of 5 stations (A to E, all
    # connected) and also links to a line P1-P2-...-P6:
    #   - A has the most connections (5), so "degree" closes A first.
    #   - P1 carries more fastest routes (25 pairs vs. A's 24), so "betweenness" closes P1 first.
    G = nx.Graph()
    for u, v in itertools.combinations("ABCDE", 2):
        add_segment(G, u, v, 1)
    add_segment(G, "A", "P1", 1)
    for i in range(1, 6):
        add_segment(G, f"P{i}", f"P{i + 1}", 1)
    assert removal_order(G, 1, "degree") == ["A"]
    assert removal_order(G, 1, "betweenness") == ["P1"]


def test_closing_cedar_junction_leaves_8_of_10_stations_together(sample):
    # Without Cedar Junction, Fir is cut off: the largest piece has 8 of the 10 stations.
    assert breakdown_curve(sample, 1, "betweenness") == [1.0, 0.8]


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_curve_never_goes_up(sample, strategy):
    curve = breakdown_curve(sample, 10, strategy)
    assert all(later <= earlier for earlier, later in zip(curve, curve[1:]))
    assert curve[-1] == 0.0   # every station removed


def test_original_network_is_unchanged(sample):
    breakdown_curve(sample, 5, "betweenness")
    assert sample.number_of_nodes() == 10


# --- Bad input -----------------------------------------------------------------------------

def test_unknown_strategy_raises(sample):
    with pytest.raises(ValueError):
        breakdown_curve(sample, 3, "biggest")


@pytest.mark.parametrize("k", [-1, 11])
def test_k_outside_0_to_station_count_raises(sample, k):
    with pytest.raises(ValueError):
        breakdown_curve(sample, k, "degree")


def test_random_has_no_fixed_removal_order(sample):
    with pytest.raises(ValueError):
        removal_order(sample, 3, "random")
