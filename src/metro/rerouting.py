import networkx as nx
from .graph import close_stations


def find_route(G, start, end):
    # Check if the starting and ending stations exist
    if start not in G or end not in G:
        return None

    try:
        # Find the fastest path based on travel time
        path = nx.shortest_path(G, start, end, weight="weight")

        # Calculate the total travel time in minutes
        time = nx.shortest_path_length(
            G, start, end, weight="weight"
        )

        return path, time

    except nx.NetworkXNoPath:
        # Return None if the stations are not connected
        return None


def reroute(G, start, end, closed_stations):
    # Find the original route before closing stations
    original = find_route(G, start, end)

    # Remove the closed stations from a copy of the graph
    updated_graph = close_stations(G, closed_stations)

    # Find a new route that avoids the closed stations
    alternative = find_route(updated_graph, start, end)

    # Check how many extra minutes the new route takes
    extra_minutes = None

    if original is not None and alternative is not None:
        extra_minutes = alternative[1] - original[1]

    return {
        "original": original,
        "alternative": alternative,
        "extra_minutes": extra_minutes
    }
