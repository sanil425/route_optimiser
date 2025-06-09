"""Vehicles Routing Problem (VRP) with Time Windows."""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from gpt_interface import get_data


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

    # Automated — use location_names from GPT
    location_names = data["location_names"]
    location_durations = data["location_durations"]

    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue

        index = routing.Start(vehicle_id)
        route_text += f"Driver {vehicle_id}:\n"

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Min(time_var)

            # Format time as HH:MM
            hours = arrival_time // 60
            minutes = arrival_time % 60

            route_text += (
                f"  - {location_names[node]} at {hours}:{minutes:02d} "
                f"(stay {location_durations[node]} min)\n"
            )

            index = solution.Value(routing.NextVar(index))

        # Add last location (depot)
        node = manager.IndexToNode(index)
        time_var = time_dimension.CumulVar(index)
        arrival_time = solution.Min(time_var)
        hours = arrival_time // 60
        minutes = arrival_time % 60

        route_text += (
            f"  - {location_names[node]} at {hours}:{minutes:02d} "
            f"(stay {location_durations[node]} min)\n"
        )

    return route_text



def get_summary_from_gpt(route_text):
    import openai
    from dotenv import load_dotenv
    import os

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f"""
              Here is an optimized route:

              {route_text}

              Please write a friendly, structured summary for the user. 

              Clearly state:
              - The order of stops (use the real names provided).
              - The approximate arrival time at each stop.
              - When the user will return to the Depot / Home.

              Only mention the real names of places (do not say "Order 1", "Order 2", etc).
              Please write in bullet points but DO NOT use Markdown formatting (no **bold**).
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
    I want to plan my day with the following constraints

    - Go to the cricket store to pick something up which is open from 1 PM to 11 PM. Duration of time spent there is 10 minutes.
    - Enjoy a day at the beach sometime between 12 PM and 7 PM. Duration of time spend there is 4 hours.
    - Eat Dosa Grill for dinner sometime between 5 PM and 9 PM. Duration of time spend there is 1.5 hours.

    I am starting from home at 8:30 AM, and want to return home as early as possible.

    Please compute the best route considering these times.

    Travel times (inverse is the same):

    Home to Cricket Store: 1 hour 20 minutes
    Home to Beach: 1 hour 12 minutes
    Home to Dosa Grill: 54 minutes
    Cricket Store to Beach: 39 minutes
    Cricket Store to Dosa Grill: 30 minutes
    Beach to Dosa Grill: 41 minutes
    
    """

    data = get_data(user_instruction)

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