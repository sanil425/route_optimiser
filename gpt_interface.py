from dotenv import load_dotenv
import os
import openai
import json

load_dotenv()  # load variables from .env
openai.api_key = os.getenv("OPENAI_API_KEY")

# SYSTEM_PROMPT defines role and required output format
SYSTEM_PROMPT = """
You are a route optimization assistant.

Your task is to take a natural language description of a routing problem.
The problem may involve deliveries, errands, personal commitments, or visits to various locations — each with time constraints.

You must output only a JSON object with the following fields:

- num_vehicles (int)
- depot_time_window (list of 2 ints [start_min, end_min])  
    # start_min and end_min represent the earliest and latest time (in minutes since midnight) the user is available to start and return home.
    # If the user specifies a range of time they are free to leave from Home (e.g. "I can leave between 9 AM and 11 AM"), use depot_time_window = [540, 660].
    # If the user specifies an exact desired start time (e.g. "I want to start at 10 AM"), set depot_time_window = [600, 600].
- time_windows (list of [start_min, end_min], depot first)  
    # time windows for all locations, depot first
- depot (int index)  
    # index of depot location
- location_names (list of strings): full addresses or names geocodable by Google Maps, depot first
- location_durations (list of ints): duration (in minutes) to be spent at each location (depot first, usually 0 for depot)

Rules:
- The "Home" or "Depot" should always be location index 0.
- All lists must have the same length.
- The order of locations in location_names, time_windows, and location_durations must match exactly.
- Do NOT generate time_matrix. Travel times will be computed separately.

Respond ONLY with valid JSON. No extra text.

When later asked to summarize a route, match the voice and tone to the user's perspective:
- If the user says "I want to plan", speak to them ("you", "your stops", etc.).
- If referring to a driver or 3rd person, use "the driver", "the route", etc.
- Adjust tone to match the context of the request.
"""



def get_data(user_instruction):
  response = openai.chat.completions.create(
    model = "gpt-4o",
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_instruction},],
                temperature = 0
  )
  reply_text = response.choices[0].message.content

  # fix formatting
  reply_text = reply_text.strip()
  if reply_text.startswith("```json"):
      reply_text = reply_text[len("```json"):].strip()
  if reply_text.endswith("```"):
      reply_text = reply_text[:-3].strip()

  # convert to python dict
  data = json.loads(reply_text)

  return data

def print_data(data):
    print("Number of vehicles:", data["num_vehicles"])
    print("Depot time window:", data["depot_time_window"])
    print("Time windows:")
    for i, window in enumerate(data["time_windows"]):
        print(f"  Location {i}: {window}")
    print("Time matrix:")
    for row in data["time_matrix"]:
        print("  ", row)
    print("Depot index:", data["depot"])

if __name__ == "__main__":
  user_instruction = """
  1 driver. Depot open 9 AM to 5 PM.
  Orders A, B, C must be delivered by 12 PM, 1 PM, 2 PM.
  Travel times:
  Depot-A: 10 min
  Depot-B: 15 min
  Depot-C: 20 min
  A-B: 5 min
  A-C: 12 min
  B-C: 6 min
  """
  data = get_data(user_instruction)
  print_data(data)



