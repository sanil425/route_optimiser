"""Vehicles Routing Problem (VRP) with Time Windows."""

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

GOOGLEMAPS_API_KEY = "AIzaSyA_mnq-8XaTO8pH64EXolOrKjMnkK3dSqc"
gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)


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
    api_key="YOUR_GOOGLE_API_KEY"
):
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=api_key)

    # Geocode all addresses
    lat_list = []
    lon_list = []
    for addy in address_list:
        geocode_res = gmaps.geocode(addy)
        location = geocode_res[0]['geometry']['location']
        lat_list.append(location['lat'])
        lon_list.append(location['lng'])
        time.sleep(0.1)  # avoid hitting rate limit

    # Build ordered list of coordinates
    route_coords = [(lat_list[i], lon_list[i]) for i in visit_order]

    # Create folium map with style
    start_lat, start_lon = route_coords[0]
    m = folium.Map(location=[start_lat, start_lon], zoom_start=8, tiles=map_style)

    # Add markers for each stop
    for stop_num, i in enumerate(visit_order):
        lat = lat_list[i]
        lon = lon_list[i]
        addy = address_list[i]
        name = location_names[i]
        duration = location_durations[i]

        # Lookup arrival/departure times for this stop
        arrival_str = ""
        departure_str = ""
        for stop_info in arrival_departure_info:
            node_idx, arr_str, dep_str = stop_info
            if node_idx == i:
                arrival_str = arr_str
                departure_str = dep_str
                break

        # Build nicer popup → with arrival & departure times
        popup_text = f'''
        <div style="
            width: 250px;
            font-size: 15px;
            line-height: 1.5;
            font-family: Arial, sans-serif;
        ">
        <b>{name}</b><br>
        {addy}<br>
        Arrival: {arrival_str}<br>
        Departure: {departure_str}<br>
        {'Depot / Home' if duration == 0 else f'Time spent: {duration} minutes'}
        </div>
        '''

        # Add marker → numbered circle marker
        icon_color = 'green' if stop_num == 0 else 'red'

        folium.Marker(
            [lat, lon],
            popup=popup_text,
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color: {icon_color};
                    color: white;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    text-align: center;
                    line-height: 30px;
                    font-weight: bold;
                    font-size: 14px;
                ">{stop_num + 1}</div>
            """)
        ).add_to(m)

    # Define color palette for segments
    colors = ['blue', 'deepskyblue', 'green', 'yellowgreen', 'gold', 'orange', 'orangered', 'red']

    # Draw individual route segments using Directions API (road-following)
    for j in range(len(visit_order) - 1):
        from_i = visit_order[j]
        to_i = visit_order[j+1]

        origin = address_list[from_i]
        destination = address_list[to_i]

        # Get driving directions
        response = gmaps.directions(origin, destination, mode='driving')

        # Extract polyline and decode
        polyline_str = response[0]['overview_polyline']['points']
        decoded_points = polyline.decode(polyline_str)

        travel_time = time_matrix[from_i][to_i]
        travel_distance = distance_matrix[from_i][to_i]

        popup_text = f"Travel time: {travel_time:.1f} min, Distance: {travel_distance:.1f} km"

        # Cycle through colors
        color = colors[j % len(colors)]

        folium.PolyLine(
            decoded_points,
            color=color,
            weight=8,  # thicker line
            opacity=0.8,
            popup=popup_text
        ).add_to(m)

    # Optional: add final leg back to depot
    if return_to_start:
        from_i = visit_order[-1]
        to_i = visit_order[0]

        origin = address_list[from_i]
        destination = address_list[to_i]

        response = gmaps.directions(origin, destination, mode='driving')
        polyline_str = response[0]['overview_polyline']['points']
        decoded_points = polyline.decode(polyline_str)

        travel_time = time_matrix[from_i][to_i]
        travel_distance = distance_matrix[from_i][to_i]

        popup_text = f"Travel time: {travel_time:.1f} min, Distance: {travel_distance:.1f} km"

        # Use a distinct color for return leg
        color = colors[(len(visit_order)-1) % len(colors)]

        folium.PolyLine(
            decoded_points,
            color=color,
            weight=8,
            opacity=0.8,
            popup=popup_text
        ).add_to(m)

    # Add legend
    legend_html = '''
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        z-index: 9999;
        background-color: white;
        border:2px solid grey;
        padding: 10px;
        font-size: 14px;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.4);
    ">
    <b>Legend</b><br>
    <span style="color:red;">&#9632;</span> Depot / Home<br>
    <span style="color:blue;">&#9632;</span> Other stops<br>
    <span style="color:black;">&#8213;</span> Route segments (various colors, click to view travel time & distance)<br>
    </div>
    '''

    m.get_root().html.add_child(folium.Element(legend_html))

    # Save map
    m.save('route_map.html')
    print("Map successfully saved to route_map.html — open it in your browser!")


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
                    # First Depot → Starting point
                    route_text += (
                        f"Departure from origin, {location_addresses[node]}, at {arr_hours}:{arr_minutes:02d}.\n\n"
                    )
                else:
                    # Return to Depot at end
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
                # Not Depot → Regular stop
                if prev_departure_time is not None:
                    travel_time = arrival_time - prev_departure_time
                    travel_hours = travel_time // 60
                    travel_minutes = travel_time % 60
                    route_text += (
                        f"Travel to {location_names[node]}, {location_addresses[node]}. "
                        f"Travel time is {travel_hours} hours and {travel_minutes} minutes. "
                        f"You will arrive at {location_names[node]} at {arr_hours}:{arr_minutes:02d}.\n"
                    )

                # Stay at location
                route_text += (
                    f"Stay at {location_names[node]} for {location_durations[node]} minutes "
                    f"from {arr_hours}:{arr_minutes:02d} to {dep_hours}:{dep_minutes:02d}. "
                    f"Departure from {location_names[node]} at {dep_hours}:{dep_minutes:02d}.\n\n"
                )

            # Update tracker
            prev_departure_time = departure_time
            is_first_stop = False

            index = solution.Value(routing.NextVar(index))

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



def main():
    user_instruction = load_user_instruction('user_instruction_scenarios.txt', 'After Work Groceries')
    data = get_data(user_instruction)
    check_depot(data) 

    # fallback in case model returns depot_time_window instead of newer keys
    if "depot_departure_window" not in data and "depot_time_window" in data:
        data["depot_departure_window"] = data["depot_time_window"]
        data["depot_return_window"] = data["depot_time_window"]

    time_matrix = get_time_matrix(data["location_addresses"], gmaps)
    data["time_matrix"] = time_matrix

    distance_matrix = get_distance_matrix(data["location_addresses"], gmaps)
    data["distance_matrix"] = distance_matrix

    # Create routing manager
    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]), data["num_vehicles"], data["depot"]
    )

    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = data["time_matrix"][from_node][to_node]
        service_time = data["location_durations"][from_node] if from_node != data["depot"] else 0
        return travel_time + service_time

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    routing.AddDimension(
        transit_callback_index,
        10000,
        10000,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    for location_idx, window in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(window[0], window[1])

    depot_idx = data["depot"]
    for vehicle_id in range(data["num_vehicles"]):
        start_idx = routing.Start(vehicle_id)
        end_idx = routing.End(vehicle_id)
        time_dimension.CumulVar(start_idx).SetRange(*data["depot_departure_window"])
        time_dimension.CumulVar(end_idx).SetRange(*data["depot_return_window"])

    # OPTIMIZED OBJECTIVE → minimize total journey time (end - start)
    start_time = time_dimension.CumulVar(routing.Start(0))
    end_time = time_dimension.CumulVar(routing.End(0))

    # Maximize start time (leave as late as possible)
    routing.AddVariableMaximizedByFinalizer(start_time)

    # Minimize end time (finish as early as possible)
    routing.AddVariableMinimizedByFinalizer(end_time)

    print("INFO: Optimizing for shortest total journey time (end - start)")

    # Solve
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        # Debug: print optimized start/end
        print("Optimized start time (min from midnight):", solution.Min(start_time))
        print("Optimized end time (min from midnight):", solution.Min(end_time))
        print("Total journey time (min):", solution.Min(end_time) - solution.Min(start_time))

        # Extract route text
        route_text = extract_route_text(data, manager, routing, solution)

        # Build visit order
        visit_order = []
        index = routing.Start(0)  # vehicle id = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            visit_order.append(node_index)
            index = solution.Value(routing.NextVar(index))

        # Create map
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

        # GPT summary
        summary = get_summary_from_gpt(route_text)
        print("AI summary of route:")
        print(summary)
        print("\n")



# helpers
def check_depot(data):
    """Sanity check to ensure Home is first stop."""
    #print("Depot index:", data["depot"])
    #print("First location name:", data["location_names"][0])
    #print("Full location names:", data["location_names"])

    if data["depot"] != 0:
        print("WARNING: Depot is not first stop! Check user prompt or get_data().")

    if "Home" not in data["location_names"][0] and "Hannum Drive" not in data["location_names"][0] and "Lancaster Ave" not in data["location_names"][0]:
        print("WARNING: First stop is not Home! LLM may have failed to parse Home correctly.")
def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f"Objective: {solution.ObjectiveValue()}")
    time_dimension = routing.GetDimensionOrDie("Time")
    total_time = 0
    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            plan_output += (
                f"{manager.IndexToNode(index)}"
                f" Time({solution.Min(time_var)},{solution.Max(time_var)})"
                " -> "
            )
            index = solution.Value(routing.NextVar(index))
        time_var = time_dimension.CumulVar(index)
        plan_output += (
            f"{manager.IndexToNode(index)}"
            f" Time({solution.Min(time_var)},{solution.Max(time_var)})\n"
        )
        plan_output += f"Time of the route: {solution.Min(time_var)}min\n"
        print(plan_output)
        total_time += solution.Min(time_var)
    print(f"Total time of all routes: {total_time}min")
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




if __name__ == "__main__":
    main()  





 