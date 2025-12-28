"""
Flask web application for X-Ray dashboard.
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import sys

# Add parent directory to path to import xray
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from xray.storage import Storage

app = Flask(__name__)
storage = Storage()


@app.route('/')
def index():
    """Home page with execution list."""
    return render_template('index.html')


@app.route('/api/executions')
def list_executions():
    """API endpoint to list all executions."""
    executions = storage.list_executions(limit=100)
    return jsonify(executions)


@app.route('/api/executions/<execution_id>')
def get_execution(execution_id):
    """API endpoint to get a specific execution."""
    execution = storage.get_execution(execution_id)
    if not execution:
        return jsonify({"error": "Execution not found"}), 404
    return jsonify(execution)


@app.route('/execution/<execution_id>')
def execution_detail(execution_id):
    """Detail page for a specific execution."""
    return render_template('execution_detail.html', execution_id=execution_id)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

