from dotenv import load_dotenv
import os
import openai
import json

load_dotenv()
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
- precedence_constraints: list of pairs of strings  
- num_vehicles: always set to 1

**Additional behavior for vague phrases**:

If the user uses vague language, infer values as follows:

- "evening" → [1020, 1260] (17:00 to 21:00)
- "morning" → [360, 720] (6:00 to 12:00)
- "afternoon" → [720, 1020] (12:00 to 17:00)
- "lunchtime" → [690, 810] (11:30 to 13:30)
- "late night" → [1260, 1439] (21:00 to midnight)
- "quick visit", "drop by" → 10–15 minutes
- "some time", "a few hours" → 120–180 minutes
- If no time or duration is given, assume wide windows [0, 1439] and 0–60 min duration.

**Depot handling**:
- If "leave at X", convert to minutes after midnight and set depot_departure_window = (X, X).
- If "return home by Y", set depot_return_window = (0, Y).
- If "return home as early as possible", use wide window (0, 1439).
- If "end at X", append X and set custom_end_index to that index.

**Output format**:
Only return valid JSON. No markdown or extra text.
"""

def get_data(user_instruction):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_instruction},
        ],
        temperature=0.2
    )

    reply_text = response.choices[0].message.content.strip()

    # Strip markdown block if GPT adds it
    if reply_text.startswith("```json"):
        reply_text = reply_text[len("```json"):].strip()
    if reply_text.endswith("```"):
        reply_text = reply_text[:-3].strip()

    try:
        data = json.loads(reply_text)
    except Exception as e:
        print("Failed to parse GPT JSON:", reply_text)
        raise e

    # Sanity check
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
