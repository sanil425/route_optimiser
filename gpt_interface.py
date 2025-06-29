from dotenv import load_dotenv
import os
import openai
import json

load_dotenv()  # load variables from .env
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
You are an assistant that helps plan optimal driving routes for users.  

You will receive natural language instructions describing a day of errands or trips.  
You must parse the instruction and extract a structured data object representing the stops and timing constraints.  

Your goal is to enable a solver to compute an optimal route that respects time windows and durations at each stop.

Your output must be a **pure JSON object** with these fields:

- location_addresses: list of strings → each stop's full address (first must be the origin / depot)
- location_names: list of strings → each stop's name (first must be the origin / depot)
- location_durations: list of integers → time to spend at each stop, in minutes (0 for depot / home)
- time_windows: list of pairs (open_time, close_time), in minutes from midnight → allowed arrival window for each stop
- depot: integer → index of the depot (origin) → must always be 0
- depot_departure_window: pair (earliest_departure_time, latest_departure_time), in minutes from midnight
- depot_return_window: pair (earliest_return_time, latest_return_time), in minutes from midnight
- custom_end_index: optional integer → if specified, this index is the final stop and the route should end there instead of returning to the depot
- precedence_constraints: list of pairs of strings.  
  If the user says that a stop "must be the first stop" or "first do X", generate precedence_constraints that place this stop before ALL other non-Home stops.  
  Example: if Stop A must be first and other stops are [Stop B, Stop C], generate: "precedence_constraints": [["Stop A", "Stop B"], ["Stop A", "Stop C"]]
  If the user says "Then do X", generate precedence_constraints between the previous stop and X.  
  Always include "precedence_constraints", even if empty.
- num_vehicles: always set to 1

Important behavior and parsing rules:

**Depot (Origin)**:
- The first stop must always be the depot (origin).
- If the user says "I want to leave from Home (address) at TIME", set depot = 0 and set depot_departure_window = (TIME, TIME).
- If no leave time is given, assume a default wide window (e.g. (0, 1439)).
- If the user says "leave as late as possible", do NOT generate an exact single time.  
  Generate a flexible window — e.g. (latest feasible time minus 20 min, latest feasible time).  
  This allows the solver flexibility to choose a feasible departure time.
- depot_return_window should normally be wide (e.g. (0, 1439)), unless user specifies otherwise (e.g. "return home by 5 PM").
- If the user says "end the trip at X", then add that as the last stop and set custom_end_index to its index. In this case, do not return to the depot.

**Handling time window phrases**:
- If the instruction says "arrive at X", "must arrive at X", or "pick up at X", you MUST generate a tight time window where open_time == close_time == X (exact arrival required).
- If the instruction says "between X and Y", generate a time window (X → Y) accordingly.
- If the instruction says "open from X to Y", generate a time window (X → Y).
- If no time is specified for a stop, assume a default wide window (e.g. (0, 1439)).
- Be very precise when parsing time expressions. "5:45 PM" must be parsed as 17:45 (NOT 17:25). Use strict time parsing.

**Handling durations**:
- If the instruction says "stay for N minutes" or "stop for N minutes", set location_duration = N.
- If the instruction says "stay for N hours", convert to minutes.
- If no duration is specified, use a default of 0 minutes.

**Handling special phrases**:
- "Return home as early as possible" → set depot_return_window = (0, 1439).
- "Must be the first thing done" → this means that the stop must appear early in the route and you should use an exact time window if possible, and precedence_constraints must be generated to enforce this stop occurs before all others (except Home).
- "Pick up my friend at X" → treat as "arrive exactly at X".
- "End the trip at Columbia University" → append Columbia University as the last stop and set custom_end_index to its index. Do not return to the depot.

**Output format**:
- You must output a pure JSON object.  
- No extra text.  
- No comments.  
- No Markdown.  
- No "Here is the data:" or "```json" blocks.  
- Only output valid JSON.

Example correct output:

{
    "location_addresses": ["Home Address", "Stop 1 Address", "Stop 2 Address", ...],
    "location_names": ["Home", "Stop 1 Name", "Stop 2 Name", ...],
    "location_durations": [0, 10, 60, ...],
    "time_windows": [[660, 660], [720, 720], [780, 900], ...],
    "depot": 0,
    "depot_departure_window": [660, 660],
    "depot_return_window": [0, 1439],
    "custom_end_index": 3,
    "precedence_constraints": [],
    "num_vehicles": 1
}

Be precise, consistent, and unambiguous in your parsing.  
When in doubt, prefer to use exact times rather than wide windows.

Your job is to help the solver compute an accurate and realistic driving plan based on the user's natural language instruction.
"""

def get_data(user_instruction):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_instruction},
        ],
        temperature=0
    )
    reply_text = response.choices[0].message.content

    # Clean response
    reply_text = reply_text.strip()
    if reply_text.startswith("```json"):
        reply_text = reply_text[len("```json"):].strip()
    if reply_text.endswith("```"):
        reply_text = reply_text[:-3].strip()

    data = json.loads(reply_text)

    # Optional validation
    if "custom_end_index" in data:
        assert 0 <= data["custom_end_index"] < len(data["location_names"]), "Invalid custom_end_index"

    return data

def print_data(data):
    print("Number of vehicles:", data["num_vehicles"])
    print("Depot index:", data["depot"])
    print("Depot departure window:", data["depot_departure_window"])
    print("Depot return window:", data["depot_return_window"])
    if "custom_end_index" in data:
        print("Custom end index:", data["custom_end_index"])
        print("Custom end location:", data["location_names"][data['custom_end_index']])
    print("Time windows:")
    for i, window in enumerate(data["time_windows"]):
        print(f"  Location {i}: {window}")


