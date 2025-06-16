# utils.py
def load_user_instruction(file_path, scenario_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    scenarios = content.split('=== ')
    for scenario in scenarios:
        if scenario.strip().startswith(f"Scenario: {scenario_name}"):
            return '\n'.join(scenario.strip().split('\n')[1:]).strip()
    raise ValueError(f"Scenario '{scenario_name}' not found in {file_path}.")

def check_depot(data):
    if data["depot"] != 0:
        print("WARNING: Depot is not first stop!")
    if "Home" not in data["location_names"][0] and "Hannum Drive" not in data["location_names"][0] and "Lancaster Ave" not in data["location_names"][0]:
        print("WARNING: First stop may not be Home.")

def extract_route_text(data, manager, routing, solution):
    time_dimension = routing.GetDimensionOrDie("Time")
    route_text = ""
    location_names = data["location_names"]
    location_addresses = data["location_addresses"]
    location_durations = data["location_durations"]
    arrival_departure_info = []

    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue

        index = routing.Start(vehicle_id)
        prev_departure_time = None
        is_first_stop = True

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Min(time_var)
            departure_time = arrival_time + location_durations[node]

            arr_str = f"{arrival_time // 60}:{arrival_time % 60:02d}"
            dep_str = f"{departure_time // 60}:{departure_time % 60:02d}"
            arrival_departure_info.append((node, arr_str, dep_str))

            if node == data["depot"]:
                if is_first_stop:
                    route_text += f"Departure from origin, {location_addresses[node]}, at {arr_str}.\n\n"
                else:
                    if prev_departure_time is not None:
                        travel_time = arrival_time - prev_departure_time
                        route_text += f"Travel back to origin, {location_addresses[node]}. Travel time is {travel_time // 60} hours and {travel_time % 60} minutes. You will arrive back at your origin at {arr_str}. Your total journey was {arrival_time} minutes.\n"
            else:
                if prev_departure_time is not None:
                    travel_time = arrival_time - prev_departure_time
                    route_text += f"Travel to {location_names[node]}, {location_addresses[node]}. Travel time is {travel_time // 60} hours and {travel_time % 60} minutes. You will arrive at {location_names[node]} at {arr_str}.\n"
                route_text += f"Stay at {location_names[node]} for {location_durations[node]} minutes from {arr_str} to {dep_str}. Departure from {location_names[node]} at {dep_str}.\n\n"

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

    prompt = f"""Here is an optimized route, structured as a full schedule:
{route_text}
Please write a detailed schedule plan for the user.
[... same prompt as you used before ...]"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a friendly assistant helping explain delivery routes."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
