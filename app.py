from flask import Flask, request, jsonify
from vrptw import run_vrptw
from dotenv import load_dotenv
import os

load_dotenv()  
GOOGLEMAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/solve', methods=['POST'])
def solve():
    data = request.get_json()  # get json body from request
    instruction = data.get("instruction", "")  # extract instruction
    result = run_vrptw(instruction)
    return jsonify(result)

if __name__ == '__main__':
    # Bind to the port Render provides via environment variable PORT (default 5000 if not set)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
