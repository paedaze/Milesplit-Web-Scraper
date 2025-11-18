import sqlite3

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS


# Function to convert string to enum
def string_to_enum(Enum, string):
    for enum in Enum:
        if enum.name == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum name")


app = Flask(__name__)
CORS(app)


def load_school_map():
    """Read the GA Milesplit school data from the SQLite database."""
    with sqlite3.connect('ga-milesplit-school-database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, link FROM gamilesplitschools ORDER BY name")
        schools = cursor.fetchall()
    return {name: link for name, link in schools}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schools", methods=['GET'])
def schools():
    return jsonify(load_school_map())

@app.route("/api/process-virtual-meet", methods=['POST'])
def simulate_meet():
    data = request.json

    for key, value in data.items():
        print(f"{key}: {value}")

    return jsonify({
        'status': 'success',
        'message': f'Successfully received items.'
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
