from flask import Flask, render_template, request
from vrptw import run_vrptw

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    instruction = ""
    summary = explanation = stats = None
    map_path = None

    if request.method == "POST":
        instruction = request.form.get("instruction", "")

        # Call your route logic
        map_file, summary_text, trip_summary, explanation, *_ = run_vrptw(instruction)

        if summary_text:
            summary = summary_text.replace("\n", "<br>")

        if trip_summary:
            stats = {
                "total_stops": trip_summary.get("total_stops"),
                "total_distance": round(trip_summary.get("total_distance", 0), 2),
                "total_travel_time": trip_summary.get("total_travel_time"),
                "total_stop_time": trip_summary.get("total_stop_time"),
                "start_time": trip_summary.get("start_time"),
                "end_time": trip_summary.get("end_time")
            }

        map_path = "route_map.html" if map_file else None

    return render_template(
        "index.html",
        instruction=instruction,
        summary=summary,
        stats=stats,
        explanation=explanation,
        map_path=map_path
    )

if __name__ == "__main__":
    app.run(debug=True)
