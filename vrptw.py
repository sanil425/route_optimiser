"""Vehicles Routing Problem (VRP) with Time Windows."""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from gpt_interface import get_data
import googlemaps
from maps import get_time_matrix


GOOGLEMAPS_API_KEY = "AIzaSyA_mnq-8XaTO8pH64EXolOrKjMnkK3dSqc"
gmaps = googlemaps.Client(key=GOOGLEMAPS_API_KEY)


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

def extract_route_text(data, manager, routing, solution):
    time_dimension = routing.GetDimensionOrDie("Time")
    route_text = ""

    location_names = data["location_names"]
    location_durations = data["location_durations"]

    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue

        index = routing.Start(vehicle_id)
        route_text += f"Driver {vehicle_id}:\n"

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

            # Special handling for Home (depot)
            if node == data["depot"]:
                if is_first_stop:
                    # First Home → starting point
                    route_text += f"Starting from Home at {arr_hours}:{arr_minutes:02d}\n"
                else:
                    # Return to Home at end
                    if prev_departure_time is not None:
                        travel_time = arrival_time - prev_departure_time
                        travel_hours = travel_time // 60
                        travel_minutes = travel_time % 60
                        route_text += (
                            f"    Travel time to Home: {travel_hours}h {travel_minutes}m\n"
                        )
                    route_text += f"Returning Home at {arr_hours}:{arr_minutes:02d}\n"
            else:
                # Not depot → regular stop
                if prev_departure_time is not None:
                    travel_time = arrival_time - prev_departure_time
                    travel_hours = travel_time // 60
                    travel_minutes = travel_time % 60
                    route_text += (
                        f"    Travel time to {location_names[node]}: {travel_hours}h {travel_minutes}m\n"
                    )

                route_text += (
                    f"  - {location_names[node]}: {arr_hours}:{arr_minutes:02d} to {dep_hours}:{dep_minutes:02d} "
                    f"(stay {location_durations[node]} min)\n"
                )

            # Update tracker
            prev_departure_time = departure_time
            is_first_stop = False

            index = solution.Value(routing.NextVar(index))

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

    Please write a **detailed planner-style summary** for the user.

    For each step, clearly state:
    - The exact **departure time** from Home or from the previous stop.
    - The **travel time** to the next location (in hours and minutes).
    - The **arrival time** at the next location.
    - The **time range spent at that location** (from HH:MM to HH:MM).
    - Repeat this structure for the entire day, until returning Home.

    Be explicit about **when the user leaves each location** and **how long the travel is** to the next one. The output should be like a personal schedule the user can follow.

    Only mention the **real names of locations** (do not say "Order 1", "Order 2", etc). Do NOT use Markdown formatting (no bold, no bullet points). Write it as clear text the user can read and follow.
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
    """Solve the VRP with time windows."""
    # Instantiate the data problem.
    user_instruction = """
    I want to plan my day with the following constraints:

    - I want to leave from home at 370 W Lancaster Ave, Haverford, PA at 10 AM. I would like to return as early as possible.
    - Go to the cricket store at 4440 Bordentown Ave, Old Bridge, NJ. It's open from 1 PM to 11 PM, and I will spend about 10 minutes there.
    - Enjoy a day at the beach at Bradshaw Beach, located at 1 Washington Avenue, Point Pleasant Beach, NJ, sometime between 12 PM and 7 PM. I want to spend 4 hours there.
    - Eat dinner at Dosa Grill, 1980 State Route 27 Ste 3, North Brunswick, NJ between 5 PM and 9 PM. I will stay for 1.5 hours.

    Please plan the most efficient route for the day considering these constraints.
    """

    data = get_data(user_instruction)

    # print checking
    print("GPT location names:", data["location_names"])
    print("GPT location durations:", data["location_durations"])
    print("GPT time windows:", data["time_windows"])

    location_names = data["location_names"]
    if not location_names:
        print("Error: GPT did not return location_names. Please check your SYSTEM_PROMPT or user instruction.")
        return

    time_matrix = get_time_matrix(location_names, gmaps)
    data["time_matrix"] = time_matrix

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]), data["num_vehicles"], data["depot"]
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def time_callback(from_index, to_index):
      """Returns the travel time between the two nodes + service time at from_node."""
      from_node = manager.IndexToNode(from_index)
      to_node = manager.IndexToNode(to_index)
      
      # Base travel time
      travel_time = data["time_matrix"][from_node][to_node]
      
      # Service time: we model this as waiting at "from_node"
      service_time = data["location_durations"][from_node] if from_node != data["depot"] else 0
      
      return travel_time + service_time

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Time Windows constraint.
    time = "Time"
    routing.AddDimension(
        transit_callback_index,
        10000,  # allow waiting time
        10000,  # maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time,
    )
    time_dimension = routing.GetDimensionOrDie(time)
    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(data["time_windows"]):
        if location_idx == data["depot"]:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    depot_idx = data["depot"]
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            data["time_windows"][depot_idx][0], data["time_windows"][depot_idx][1]
        )

    # Instantiate route start and end times to produce feasible times.
    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
        route_text = extract_route_text(data, manager, routing, solution)
        print("Route text:", route_text)

        # send to GPT for friendly summary
        summary = get_summary_from_gpt(route_text)
        print("GPT summary of route:")
        print(summary)
        print("\n")

if __name__ == "__main__":
    main()  