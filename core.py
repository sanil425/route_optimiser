# core.py
from gpt_interface import get_data
from maps import get_time_matrix, get_distance_matrix
from visualization import visualize_route
from utils import load_user_instruction, check_depot, extract_route_text, get_summary_from_gpt

from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import googlemaps
import os

def run_vrptw(scenario_name: str):
    GOOGLEMAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")
    gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

    user_instruction = load_user_instruction('user_instruction_scenarios.txt', scenario_name)
    data = get_data(user_instruction)
    check_depot(data)

    if "depot_departure_window" not in data and "depot_time_window" in data:
        data["depot_departure_window"] = data["depot_time_window"]
        data["depot_return_window"] = data["depot_time_window"]

    data["time_matrix"] = get_time_matrix(data["location_addresses"], gmaps)
    data["distance_matrix"] = get_distance_matrix(data["location_addresses"], gmaps)

    # Setup routing
    manager = pywrapcp.RoutingIndexManager(len(data["time_matrix"]), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = data["time_matrix"][from_node][to_node]
        service_time = data["location_durations"][from_node] if from_node != data["depot"] else 0
        return travel_time + service_time

    transit_cb = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    routing.AddDimension(transit_cb, 10000, 10000, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for i, window in enumerate(data["time_windows"]):
        time_dim.CumulVar(manager.NodeToIndex(i)).SetRange(window[0], window[1])

    for v in range(data["num_vehicles"]):
        time_dim.CumulVar(routing.Start(v)).SetRange(*data["depot_departure_window"])
        time_dim.CumulVar(routing.End(v)).SetRange(*data["depot_return_window"])

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search_params)

    if not solution:
        print("No solution found.")
        return None, None, None, data

    route_text = extract_route_text(data, manager, routing, solution)

    visit_order = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        visit_order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))

    visualize_route(
        data["location_addresses"],
        visit_order,
        data["location_durations"],
        data["location_names"],
        data["distance_matrix"],
        data["time_matrix"],
        data["arrival_departure_info"],
        return_to_start=True,
        map_style='CartoDB.Voyager',
        api_key=GOOGLEMAPS_API_KEY
    )

    summary = get_summary_from_gpt(route_text)
    return route_text, summary, visit_order, data
