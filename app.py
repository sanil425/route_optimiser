from flask import Flask, request, jsonify, render_template_string
from vrptw import run_vrptw
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLEMAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        instruction = request.form.get('instruction', '')
        result = run_vrptw(instruction)
        return render_template_string("""
            <h1>Route Optimiser Result</h1>
            <pre>{{ result }}</pre>
            <a href="/">Back</a>
        """, result=result)

    # GET: show input form
    return render_template_string("""
        <h1>Route Optimiser</h1>
        <form method="post">
            <label for="instruction">Enter your instruction:</label><br>
            <input type="text" id="instruction" name="instruction" size="60" placeholder="E.g. Pick me up at 5pm"><br><br>
            <input type="submit" value="Solve">
        </form>
    """)

@app.route('/solve', methods=['POST'])
def solve():
    data = request.get_json()
    instruction = data.get("instruction", "")
    result = run_vrptw(instruction)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
