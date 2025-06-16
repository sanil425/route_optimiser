import streamlit as st
import os
import googlemaps


from utils import load_user_instruction, check_depot, extract_route_text, get_summary_from_gpt
from gpt_interface import get_data
from maps import get_time_matrix, get_distance_matrix
from visualization import visualize_route
from ortools.constraint_solver import routing_enums_pb2, pywrapcp


st.set_page_config(page_title="Route Optimizer", layout="wide")
st.title("🚐 VRPTW Route Optimizer")

instruction = st.text_area("Enter your trip description:", height=200)

if st.button("Generate Optimized Route"):
    if not instruction.strip():
        st.warning("Please enter a valid trip description.")
    else:
        # Save instruction to temporary scenario file
        with open("user_instruction_scenarios.txt", "w", encoding="utf-8") as f:
            f.write("=== Scenario: Streamlit Run ===\n" + instruction.strip())

        # Set up
        GOOGLEMAPS_API_KEY = "AIzaSyA_mnq-8XaTO8pH64EXolOrKjMnkK3dSqc"
        gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

        user_instruction = load_user_instruction("user_instruction_scenarios.txt", "Streamlit Run")
        data = get_data(user_instruction)
        check_depot(data)

        # Fallback for key
        if "depot_departure_window" not in data:
            data["depot_departure_window"] = data["depot_time_window"]
            data["depot_return_window"] = data["depot_time_window"]

        data["time_matrix"] = get_time_matrix(data["location_addresses"], gmaps)
        data["distance_matrix"] = get_distance_matrix(data["location_addresses"], gmaps)

        # Solver setup
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
            st.error("⚠️ No valid route found. Try adjusting your time windows.")
        else:
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

            st.success("✅ Route optimization complete!")

            st.subheader("🗺️ Map")
            with open("route_map.html", "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=600)

            st.subheader("📋 Route Summary")
            st.text_area("Generated Itinerary", get_summary_from_gpt(route_text), height=300)
