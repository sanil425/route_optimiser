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
    data = request.get_json(force=True)  # force=True ensures JSON parsing even without header
    instruction = data.get("instruction", "")
    result = run_vrptw(instruction)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
