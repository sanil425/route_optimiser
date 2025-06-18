from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from gpt_interface import get_data
import googlemaps
import folium
from folium.plugins import AntPath
import time
from maps import get_time_matrix
from maps import get_distance_matrix
import polyline
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLEMAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

# helpers 
def build_matrices(data, gmaps):
    """
    Adds travel time and distance matrices to the data dictionary using Google Maps.
    """
    addresses = data["location_addresses"]
    data["time_matrix"] = get_time_matrix(addresses, gmaps)
    data["distance_matrix"] = get_distance_matrix(addresses, gmaps)

def parse_instruction(instruction):
    """
    Parses the user's natural language instruction into structured routing data.
    Fills in fallback depot windows if needed.
    """
    data = get_data(instruction)

    if "depot_departure_window" not in data and "depot_time_window" in data:
        data["depot_departure_window"] = data["depot_time_window"]
        data["depot_return_window"] = data["depot_time_window"]

    # Simple check
    if data["depot"] != 0:
        print("⚠️ Warning: Depot index is not zero. Check the instruction format.")

    return data

def load_user_instruction(file_path, scenario_name):
    """Load the user instruction for a given scenario name."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Split by === to find scenarios
    scenarios = content.split('=== ')
    for scenario in scenarios:
        if scenario.strip().startswith(f"Scenario: {scenario_name}"):
            # Remove the first line and return the rest
            return '\n'.join(scenario.strip().split('\n')[1:]).strip()
    raise ValueError(f"Scenario '{scenario_name}' not found in {file_path}.")


def visualize_route(
    address_list,
    visit_order,
    location_durations,
    location_names,
    distance_matrix,
    time_matrix,
    arrival_departure_info,
    return_to_start=True,
    map_style='CartoDB positron',
    api_key=""
):
    """
    Creates an interactive Folium map of the optimized route with rich popups.
    """
    gmaps = googlemaps.Client(key=api_key)

    # Geocode all addresses to get lat/lon
    lat_list = []
    lon_list = []
    for addy in address_list:
        loc = gmaps.geocode(addy)[0]['geometry']['location']
        lat_list.append(loc['lat'])
        lon_list.append(loc['lng'])
        time.sleep(0.1)

    route_coords = [(lat_list[i], lon_list[i]) for i in visit_order]
    m = folium.Map(location=route_coords[0], zoom_start=10, tiles=map_style)

    # Build lookup for arrival/departure
    time_lookup = {node: (arr, dep) for node, arr, dep in arrival_departure_info}

    # Add markers
    for stop_num, node in enumerate(visit_order):
        if stop_num == len(visit_order) - 1 and return_to_start:
            continue
        arrival, departure = time_lookup.get(node, ("?", "?"))
        popup = f"""<div style='width: 280px; font-size: 14px; font-family: Arial; line-height: 1.5'>
        <b style="font-size: 16px;">{location_names[node]}</b><br>
        <span style='font-size:13px'>{address_list[node]}</span><br><br>
        <b>Arrival:</b> {arrival}<br>
        <b>Departure:</b> {departure}<br>
        <b>Time Spent:</b> {'Depot / Home' if location_durations[node] == 0 else f"{location_durations[node]} minutes"}
        </div>"""
        icon_color = 'green' if stop_num == 0 else 'red'
        folium.Marker(
            [lat_list[node], lon_list[node]],
            popup=popup,
            icon=folium.DivIcon(html=f"""
                <div style='background-color: {icon_color}; color: white; border-radius: 50%;
                            width: 30px; height: 30px; text-align: center; line-height: 30px;
                            font-weight: bold; font-size: 14px;'>{stop_num + 1}</div>""")
        ).add_to(m)

    # Draw segments
    colors = ['blue', 'green', 'orange', 'purple', 'gold', 'pink', 'gray']
    for i in range(len(visit_order) - 1):
        from_i = visit_order[i]
        to_i = visit_order[i + 1]
        origin = address_list[from_i]
        destination = address_list[to_i]
        directions = gmaps.directions(origin, destination, mode='driving')
        if directions:
            poly = directions[0]['overview_polyline']['points']
            decoded = polyline.decode(poly)
            travel_time = time_matrix[from_i][to_i]
            travel_dist = distance_matrix[from_i][to_i]
            from_dep = time_lookup.get(from_i, ("", ""))[1]
            to_arr = time_lookup.get(to_i, ("", ""))[0]

            popup = f"""
            <div style='width: 320px; font-size: 14px; font-family: Arial; line-height: 1.6'>
            <b style="font-size: 15px;">Route Segment</b><br>
            <b>From:</b> {location_names[from_i]}<br>
            <span style='font-size:13px'>{address_list[from_i]}</span><br>
            <b>To:</b> {location_names[to_i]}<br>
            <span style='font-size:13px'>{address_list[to_i]}</span><br><br>
            <b>Departure:</b> {from_dep}<br>
            <b>Arrival:</b> {to_arr}<br>
            <b>Travel Time:</b> {travel_time:.1f} min<br>
            <b>Distance:</b> {travel_dist:.1f} km
            </div>
            """

            folium.PolyLine(
                decoded,
                color=colors[i % len(colors)],
                weight=7,
                opacity=0.85,
                popup=popup
            ).add_to(m)

    # Return to depot
    if return_to_start:
        from_i = visit_order[-1]
        to_i = visit_order[0]
        directions = gmaps.directions(address_list[from_i], address_list[to_i], mode='driving')
        if directions:
            poly = directions[0]['overview_polyline']['points']
            decoded = polyline.decode(poly)
            travel_time = time_matrix[from_i][to_i]
            travel_dist = distance_matrix[from_i][to_i]
            from_dep = time_lookup.get(from_i, ("", ""))[1]
            to_arr = time_lookup.get(to_i, ("", ""))[0]

            popup = f"""
            <div style='width: 320px; font-size: 14px; font-family: Arial; line-height: 1.6'>
            <b style="font-size: 15px;">Return to Depot</b><br>
            <b>From:</b> {location_names[from_i]}<br>
            <span style='font-size:13px'>{address_list[from_i]}</span><br>
            <b>To:</b> {location_names[to_i]}<br>
            <span style='font-size:13px'>{address_list[to_i]}</span><br><br>
            <b>Departure:</b> {from_dep}<br>
            <b>Arrival:</b> {to_arr}<br>
            <b>Travel Time:</b> {travel_time:.1f} min<br>
            <b>Distance:</b> {travel_dist:.1f} km
            </div>
            """
            folium.PolyLine(
                decoded,
                color='black',
                weight=7,
                opacity=0.9,
                popup=popup
            ).add_to(m)

    m.save("route_map.html")
    print("✅ Map saved as route_map.html")


def extract_route_text(data, manager, routing, solution):
    time_dimension = routing.GetDimensionOrDie("Time")
    route_text = ""

    location_names = data["location_names"]
    location_addresses = data["location_addresses"]
    location_durations = data["location_durations"]
    arrival_departure_info = []  # list of (stop index, arrival time string, departure time string)

    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue

        index = routing.Start(vehicle_id)
        route_text += f"Driver {vehicle_id}:\n\n"

        # Track departure_time from previous stop
        prev_departure_time = None
        is_first_stop = True

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Min(time_var)
            departure_time = arrival_time + location_durations[node]

            arr_hours = arrival_time // 60
            arr_minutes = arrival_time % 60
            dep_hours = departure_time // 60
            dep_minutes = departure_time % 60

            # Build arrival/departure strings
            arrival_time_str = f"{arr_hours}:{arr_minutes:02d}"
            departure_time_str = f"{dep_hours}:{dep_minutes:02d}"

            # Add to arrival_departure_info
            arrival_departure_info.append((node, arrival_time_str, departure_time_str))

            if node == data["depot"]:
                if is_first_stop:
                    route_text += (
                        f"Departure from origin, {location_addresses[node]}, at {arr_hours}:{arr_minutes:02d}.\n\n"
                    )
                else:
                    if prev_departure_time is not None:
                        travel_time = arrival_time - prev_departure_time
                        travel_hours = travel_time // 60
                        travel_minutes = travel_time % 60
                        route_text += (
                            f"Travel back to origin, {location_addresses[node]}. "
                            f"Travel time is {travel_hours} hours and {travel_minutes} minutes. "
                            f"You will arrive back at your origin at {arr_hours}:{arr_minutes:02d}. "
                            f"Your total journey was {arrival_time} minutes.\n"
                        )
            else:
                if prev_departure_time is not None:
                    travel_time = arrival_time - prev_departure_time
                    travel_hours = travel_time // 60
                    travel_minutes = travel_time % 60
                    route_text += (
                        f"Travel to {location_names[node]}, {location_addresses[node]}. "
                        f"Travel time is {travel_hours} hours and {travel_minutes} minutes. "
                        f"You will arrive at {location_names[node]} at {arr_hours}:{arr_minutes:02d}.\n"
                    )
                route_text += (
                    f"Stay at {location_names[node]} for {location_durations[node]} minutes "
                    f"from {arr_hours}:{arr_minutes:02d} to {dep_hours}:{dep_minutes:02d}. "
                    f"Departure from {location_names[node]} at {dep_hours}:{dep_minutes:02d}.\n\n"
                )

            prev_departure_time = departure_time
            is_first_stop = False
            index = solution.Value(routing.NextVar(index))

        # 🔧 Handle final stop (likely return to depot)
        if routing.IsEnd(index):
            node = manager.IndexToNode(index)
            arrival_time = solution.Min(time_dimension.CumulVar(index))
            arr_hours, arr_minutes = divmod(arrival_time, 60)
            arrival_time_str = f"{arr_hours}:{arr_minutes:02d}"

            # Add to arrival_departure_info
            arrival_departure_info.append((node, arrival_time_str, arrival_time_str))

            # Append final message
            route_text += (
                f"Travel back to origin. You will arrive back at your origin at {arrival_time_str}.\n"
            )

    data["arrival_departure_info"] = arrival_departure_info
    return route_text



def get_summary_from_gpt(route_text):
    import openai
    from dotenv import load_dotenv
    import os

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f"""
    Here is an optimized route, structured as a full schedule:

    {route_text}

    Please write a detailed schedule plan for the user.

    For each step, clearly state:
    - The location name and address of the **departure location**, and the time of departure.
    - The **travel time** to the next location (in hours and minutes).
    - The location name and address of the **arrival location**, and the time of arrival.
    - The **time spent at the arrival location**, and the time frame (from HH:MM to HH:MM), unless the arrival location is the origin.
    - **Always include the return trip to the origin** at the end of the schedule, with the travel time and final arrival time at the origin.

    Be explicit about when the user departs each location, how long the travel takes, and when they arrive. The output should feel like a personal itinerary the user can follow step by step.

    Only use real names and addresses of the locations. Do NOT say "Stop 1", "Order 2", etc.
    Do NOT use Markdown formatting (no bold, no bullet points). Write the entire output in plain text.

    Use this structure:

    Departure from origin, (address), at (time).

    Travel to (location name), (address). Travel time is (travel time). You will arrive at (location name) at (time).
    Stay at (location name) for (duration) from (start time) to (end time).
    Departure from (location name) at (time).

    Travel to (next location name), (address)... [repeat this pattern for all stops]

    Travel back to origin. Travel time is (travel time). You will arrive back at your origin at (time). Your total journey was (end time - start time in hours and minutes)
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a friendly assistant helping explain delivery routes."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7
    )

    reply_text = response.choices[0].message.content.strip()
    return reply_text

def compute_trip_summary(data, visit_order, arrival_departure_info):
    total_distance = 0
    total_travel_time = 0
    total_stop_time = 0

    for i in range(len(visit_order) - 1):
        from_i = visit_order[i]
        to_i = visit_order[i + 1]
        total_distance += data["distance_matrix"][from_i][to_i]
        total_travel_time += data["time_matrix"][from_i][to_i]

    for idx in visit_order:
        total_stop_time += data["location_durations"][idx]

    depot = data["depot"]
    start_time = None
    end_time = None

    # ✅ Get first departure from depot
    for node, arr, dep in arrival_departure_info:
        if node == depot:
            start_time = dep
            break

    # ✅ Get last arrival at final node
    final_node = visit_order[-1]
    for node, arr, dep in reversed(arrival_departure_info):
        if node == final_node:
            end_time = arr
            break

    print("\n🧪 DEBUG: arrival_departure_info")
    for entry in arrival_departure_info:
        print(entry)

    return {
        "total_stops": len(visit_order) - 1,
        "total_distance": total_distance,
        "total_travel_time": total_travel_time,
        "total_stop_time": total_stop_time,
        "start_time": start_time or "?",
        "end_time": end_time or "?",
        "return_to_start": final_node == depot
    }





def solve_vrptw(data):
    """
    Solves the VRPTW problem and returns the manager, routing model, and solution.
    """
    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = data["time_matrix"][from_node][to_node]
        service_time = data["location_durations"][from_node] if from_node != data["depot"] else 0
        return travel_time + service_time

    transit_cb = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    routing.AddDimension(
        transit_cb,
        10000,  # buffer/slack
        10000,  # max time per vehicle
        False,  # don't force start cumul to zero
        "Time"
    )
    time_dim = routing.GetDimensionOrDie("Time")

    for i, window in enumerate(data["time_windows"]):
        time_dim.CumulVar(manager.NodeToIndex(i)).SetRange(window[0], window[1])

    for v in range(data["num_vehicles"]):
        time_dim.CumulVar(routing.Start(v)).SetRange(*data["depot_departure_window"])
        time_dim.CumulVar(routing.End(v)).SetRange(*data["depot_return_window"])

    for from_name, to_name in data.get("precedence_constraints", []):
        from_idx = data["location_names"].index(from_name)
        to_idx = data["location_names"].index(to_name)
        routing.solver().Add(
            time_dim.CumulVar(manager.NodeToIndex(from_idx)) +
            data["location_durations"][from_idx]
            <= time_dim.CumulVar(manager.NodeToIndex(to_idx))
        )

    # Optimise journey
    routing.AddVariableMaximizedByFinalizer(time_dim.CumulVar(routing.Start(0)))
    routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(0)))

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.time_limit.seconds = 10

    solution = routing.SolveWithParameters(search_params)
    if not solution:
        raise ValueError("❌ No solution found. Check time windows and constraints.")
    
    return manager, routing, solution


def run_vrptw(instruction):
    """
    Main function that takes user instruction, solves VRPTW, and returns the route output.
    """
    gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)

    # Parse, enrich, solve
    data = parse_instruction(instruction)
    build_matrices(data, gmaps)
    manager, routing, solution = solve_vrptw(data)

    # Extract visit order
    visit_order = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        visit_order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    visit_order.append(manager.IndexToNode(index))

    # Route text and summary
    route_text = extract_route_text(data, manager, routing, solution)
    trip_summary = compute_trip_summary(data, visit_order, data["arrival_departure_info"])
    summary_text = get_summary_from_gpt(route_text)

    # Generate map
    visualize_route(
        data["location_addresses"],
        visit_order,
        data["location_durations"],
        data["location_names"],
        data["distance_matrix"],
        data["time_matrix"],
        data["arrival_departure_info"],
        return_to_start=trip_summary["return_to_start"],
        api_key=GOOGLEMAPS_API_KEY
    )

    return "route_map.html", summary_text, trip_summary



def main():
    scenario_name = "No Return"
    instruction = load_user_instruction("user_instruction_scenarios.txt", scenario_name)

    #print(f"\n=== Scenario: {scenario_name} ===")
    #print(instruction)
    #print("\nSolving route...\n")

    try:
        map_file, summary, trip_summary = run_vrptw(instruction)

        print("=== Trip Summary ===")
        for key, val in trip_summary.items():
            print(f"{key.replace('_', ' ').title()}: {val}")

        print("\n=== GPT Itinerary Summary ===")
        print(summary)
        print(f"\n✅ Map saved to {map_file}")

    except Exception as e:
        print(f"❌ Error while solving route: {e}")


if __name__ == "__main__":
    main()





