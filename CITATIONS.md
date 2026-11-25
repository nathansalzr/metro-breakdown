# Citations

Every outside source this project uses: data, libraries, and references.
If you use something new (a dataset, tutorial, or Stack Overflow answer), add it here
in the same pull request.

## Data

| Source | What we use it for | Link |
|--------|--------------------|------|
| LA Metro rail schedule (GTFS) | Stations, segments, and travel times for the real network | [gitlab.com/LACMTA/gtfs_rail](https://gitlab.com/LACMTA/gtfs_rail) |
| LA Metro Developer site | Overview of Metro's open data and its terms of use | [developer.metro.net](https://developer.metro.net/) |
| OpenStreetMap map tiles | Background map in the app. Map data (c) OpenStreetMap contributors, ODbL license | [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright) |

Accessed November 2026. The download is not committed; `scripts/fetch_gtfs.py` recreates it.
`data/sample/gtfs/` is a made-up network the team wrote for testing, not real Metro data.

## Libraries

| Library | License | What we use it for | Link |
|---------|---------|--------------------|------|
| NetworkX | BSD-3-Clause | Graph model, shortest paths, centrality, connectivity | [networkx.org](https://networkx.org) |
| Streamlit | Apache-2.0 | The web app (tabs, dropdowns, results) | [streamlit.io](https://streamlit.io) |
| Plotly | MIT | The interactive map of routes and closures | [plotly.com/python](https://plotly.com/python/) |
| pytest | MIT | Automated tests | [pytest.org](https://pytest.org) |

## References

| Reference | What we used it for | Link |
|-----------|---------------------|------|
| GTFS Schedule Reference | Meaning of the GTFS files and fields we read | [gtfs.org/schedule/reference](https://gtfs.org/schedule/reference/) |
| NetworkX documentation | How each algorithm works and what it returns | [networkx.org/documentation](https://networkx.org/documentation/stable/) |
| CECS 427 course material, Prof. Kate Nguyen | Network concepts: shortest paths, centrality, articulation points, robustness | Course lectures, Fall 2026 |

## Tutorials and other help

*None yet. Add any tutorial, video, or forum answer you relied on.*
