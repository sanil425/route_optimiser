from flask import Flask, request, jsonify
from vrptw import run_vrptw

from dotenv import load_dotenv
import os

load_dotenv()  # load your .env file early

GOOGLEMAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)


@app.route('/solve', methods=['POST'])
def solve():
    data = request.get_json() # get json body from request
    instruction = data.get("instruction", "") # extract instruction
    result = run_vrptw(instruction)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)


