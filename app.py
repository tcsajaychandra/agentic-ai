"""
Flask application – UI for the SCTE-224 multi-agent converter.

Routes:
    /            – Dashboard home page
    /run         – Trigger the supervisor agent pipeline (POST)
    /results     – View conversion results
    /view/<file> – View a single SCTE-224 XML output file
"""

import os
from flask import Flask, render_template, redirect, url_for, flash, jsonify, request

from agents.supervisor import SupervisorAgent
from parsers.scte224_converter import SCTE224Converter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "source_files")
TARGET_DIR = os.path.join(BASE_DIR, "target_files")

app = Flask(__name__)
app.secret_key = "scte224-multiagent-secret"

# In-memory store for the latest run results
_latest_results = {}


@app.route("/")
def index():
    """Dashboard showing source files and action buttons."""
    source_files = []
    if os.path.isdir(SOURCE_DIR):
        source_files = sorted(os.listdir(SOURCE_DIR))

    target_files = []
    if os.path.isdir(TARGET_DIR):
        target_files = sorted(os.listdir(TARGET_DIR))

    return render_template(
        "index.html",
        source_files=source_files,
        target_files=target_files,
        results=_latest_results,
    )


@app.route("/run", methods=["POST"])
def run_agents():
    """Execute the supervisor agent pipeline."""
    global _latest_results
    try:
        supervisor = SupervisorAgent(SOURCE_DIR, TARGET_DIR)
        _latest_results = supervisor.run()
        flash("Agent pipeline completed successfully!", "success")
    except Exception as e:
        _latest_results = {"status": "error", "message": str(e)}
        flash(f"Pipeline error: {e}", "danger")
    return redirect(url_for("results"))


@app.route("/results")
def results():
    """Display the results from the latest agent run."""
    target_files = []
    if os.path.isdir(TARGET_DIR):
        target_files = sorted(os.listdir(TARGET_DIR))
    return render_template("results.html", results=_latest_results, target_files=target_files)


@app.route("/view/<path:filename>")
def view_file(filename):
    """View the contents of a generated SCTE-224 XML file."""
    file_path = os.path.join(TARGET_DIR, os.path.basename(filename))
    content = ""
    if os.path.exists(file_path):
        content = SCTE224Converter.read_output(file_path)
    return render_template("view_file.html", filename=filename, content=content)


@app.route("/api/run", methods=["POST"])
def api_run():
    """REST endpoint that returns JSON results."""
    global _latest_results
    try:
        supervisor = SupervisorAgent(SOURCE_DIR, TARGET_DIR)
        _latest_results = supervisor.run()
        return jsonify(_latest_results)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    os.makedirs(SOURCE_DIR, exist_ok=True)
    os.makedirs(TARGET_DIR, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
