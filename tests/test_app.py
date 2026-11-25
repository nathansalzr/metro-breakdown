"""Smoke tests for the Streamlit app, run on the sample network.

AppTest runs app.py without a browser, so we can pick stations and check what it shows.
After changing a widget, call .run() again (that's what a click does in the real app).
"""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def sample_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.sidebar.radio(key="source").set_value("Sample network").run()
    return at


def test_app_starts_without_errors():
    at = sample_app()
    assert not at.exception
    assert len(at.tabs) == 3


def test_trip_planner_shows_the_fastest_route():
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("G").run()
    assert not at.exception
    assert at.tabs[0].metric[0].value == "10 min"


def test_closing_a_station_shows_the_detour():
    # Closing Cedar Junction: 10 -> 13 minutes, +3 (same as tests/test_rerouting.py).
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("G")
    at.multiselect(key="closed_sample").select("C").run()
    assert not at.exception
    assert [m.value for m in at.tabs[0].metric] == ["10 min", "13 min"]
    assert at.tabs[0].metric[1].delta == "+3 min"


def test_map_shows_route_detour_and_closed_station():
    # AC4: the map draws the normal route, the detour, and the closed station.
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("G")
    at.multiselect(key="closed_sample").select("C").run()
    figure = json.loads(at.get("plotly_chart")[0].proto.spec)
    layers = [trace.get("name") for trace in figure["data"]]
    assert {"Normal route", "Detour", "Closed"} <= set(layers)
    closed = next(t for t in figure["data"] if t.get("name") == "Closed")
    assert closed["text"] == ["Cedar Junction (closed)"]


def test_closing_a_station_off_the_route_shows_no_change():
    # Juniper isn't on the Alder -> Ginkgo route, so the trip time doesn't change.
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("G")
    at.multiselect(key="closed_sample").select("J").run()
    assert not at.exception
    assert [m.value for m in at.tabs[0].metric] == ["10 min", "10 min"]
    assert at.tabs[0].metric[1].delta == "No change"


def test_minutes_text_keeps_half_minutes_so_numbers_add_up():
    # Some LA segments take 1.5 or 2.5 minutes. 40.5 + 3 must show as 43.5, not 40 + 3 = 44.
    from app import minutes_text
    assert minutes_text(62.0) == "62 min"
    assert minutes_text(40.5) == "40.5 min"
    assert minutes_text(43.5) == "43.5 min"
    assert minutes_text(0.5) == "0.5 min"   # a half-minute delay is not "No change"
    assert minutes_text(3.0000000001) == "3 min"   # float noise doesn't show up


def test_closing_a_single_point_of_failure_shows_unreachable():
    # Cedar Junction is Fir's only link, so Alder -> Fir becomes impossible.
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("F")
    at.multiselect(key="closed_sample").select("C").run()
    assert not at.exception
    assert "Unreachable" in at.tabs[0].error[0].value


def test_same_start_and_end_asks_for_two_stations():
    at = sample_app()
    at.selectbox(key="start_sample").select("A")
    at.selectbox(key="end_sample").select("A").run()
    assert not at.exception
    assert len(at.tabs[0].metric) == 0
    assert "two different stations" in at.tabs[0].info[0].value


# --- Critical stations tab (US-3) ----------------------------------------------------------

def test_critical_tab_ranks_the_busiest_stations():
    # Same order as the answer key in tests/test_centrality.py: Cedar Junction, Birch, Ginkgo.
    at = sample_app()
    table = at.tabs[1].dataframe[0].value
    assert list(table["Station"][:3]) == ["Cedar Junction", "Birch", "Ginkgo"]
    assert table["Share of fastest routes"][0] == "55.6%"   # 20 of the 36 pairs of other stations


def test_critical_tab_counts_single_points_of_failure():
    at = sample_app()
    assert [m.value for m in at.tabs[1].metric] == ["6 of 10", "6 of 11"]


def test_closing_the_busiest_station_splits_the_network():
    # The tab starts on the busiest station: closing Cedar Junction cuts off Fir.
    at = sample_app()
    assert "2 pieces: 8 and 1 stations" in at.tabs[1].warning[0].value
    figure = json.loads(at.tabs[1].get("plotly_chart")[0].proto.spec)
    layers = [trace.get("name") for trace in figure["data"]]
    assert "Piece 1 (8 stations)" in layers and "Piece 2 (1 station)" in layers and "Closed" in layers


def test_closing_an_end_station_keeps_one_piece():
    at = sample_app()
    at.selectbox(key="close_sample").select("E").run()
    assert not at.exception
    assert "one piece (9 stations)" in at.tabs[1].success[0].value
