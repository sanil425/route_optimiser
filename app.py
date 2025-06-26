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
    data = request.get_json()
    if not data or "instruction" not in data:
        return jsonify({"error": "Missing 'instruction' in JSON body"}), 400
    
    instruction = data.get("instruction", "")
    try:
        result = run_vrptw(instruction)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
