# Route Optimiser
A smart, AI-assisted route planning tool that interprets natural language instructions and builds an optimized multi-stop trip using Google Maps and OR-Tools.

# Link:
👉 [Click here to try it](https://route-optimiser.streamlit.app)  

# Functionality:
- Prompt like you are using any AI tool and it will plan your route accordingly.
- Include any time windows or committments necessary 
- Will print out a map
- Ai genearte trip summary

# Tech
- `Streamlit` — frontend UI
- `Python` — backend logic
- `OpenAI` — for parsing instructions
- `Google Maps API` — for distance & time matrices
- `OR-Tools` — for solving the VRPTW (vehicle routing with time windows)

# Sample Input
- I want to leave from Home (19 Hannum Drive, Ardmore, PA) as late as possible to pick up my friend from Ardmore Station (39 Station Rd, Ardmore, PA), exactly at 1736 hrs, and stop for 3 minutes.
- Go grocery shopping at Trader Joe's (112 Coulter Ave, Ardmore, PA) for 25 minutes. It's open from 0800 hrs to 2100 hrs.
- Stop at CVS (119 E Lancaster Ave, Ardmore, PA) for 10 minutes. It's open from 0900 hrs to 2100 hrs.
- Return home.

# Set up Insutrctions
1. **Clone the repo**  
   ```bash
   git clone https://github.com/sanil425/route_optimiser.git
   cd route_optimiser
