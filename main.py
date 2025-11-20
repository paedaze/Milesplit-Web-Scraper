import sqlite3

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from scraper import Sport, Event, Gender

# Function to convert string to enum
def string_to_enum(Enum, string):
    """Convert a string to an enum member by matching name or value."""
    for enum in Enum:
        if enum.name == string or enum.value == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum value")

# Function to convert milesplit's timing format to time in seconds
def convert_time(formatted_time):
    seconds = 0
    if ':' in formatted_time:
        colon_split = formatted_time.split(':')
        seconds += float(colon_split[0]) * 60
        seconds += float(colon_split[1])
    else:
        seconds += float(formatted_time)
    return seconds


app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schools", methods=['GET'])
def load_schools():
    """Read the GA Milesplit school data from the SQLite database."""
    with sqlite3.connect('ga-milesplit-school-database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, link FROM gamilesplitschools ORDER BY name")
        schools = cursor.fetchall()
    return jsonify({name: link for name, link in schools})


@app.route("/api/process-virtual-meet", methods=['POST'])
def simulate_meet():
    # Initialize database connection and data from post request
    conn = sqlite3.connect('athletes.db')
    cursor = conn.cursor()
    data = request.json

    # Split data from post request
    selected_schools = data['schools']
    selected_sport = string_to_enum(Sport, data['sport'])
    selected_event = string_to_enum(Event, data['event']).value
    selected_gender = string_to_enum(Gender, data['gender']).value

    varsity_athletes = []

    for school in selected_schools:
        cursor.execute('SELECT school_id FROM schools WHERE school_name = ?', (school,))
        school_id_row = cursor.fetchone()
        school_id = school_id_row[0]
        
        cursor.execute("""
            SELECT a.name, s.school_name, e.event_name, r.time FROM results r
            JOIN athletes a ON a.athlete_id = r.athlete_id
            JOIN events e ON e.event_id = r.event_id
            JOIN genders g ON g.gender_id = r.gender_id
            JOIN schools s ON s.school_id = r.school_id
            WHERE s.school_id = ? AND e.event_name = ? AND g.gender = ?
        """, (school_id, selected_event, selected_gender))

        # Get Top 7 athletes (Name, School, Event, Time, Points)
        meet_data = cursor.fetchall()

        sorted_school_athletes = sorted(meet_data, key=lambda entry: convert_time(entry[3]))[:7] # Sort a school's athletes and grab the top 7
        if len(sorted_school_athletes) < 5 and selected_sport == Sport.CROSS_COUNTRY: # School is not valid for scoring if team has less than 5 athletes
            for entry in sorted_school_athletes:
                varsity_athletes.append(entry + (-1,))
        else: # Otherwise, School is valid for scoring
            for entry in sorted_school_athletes:
                varsity_athletes.append(entry)

    # Sort every varsity athlete from every school by time
    varsity_athletes = sorted(varsity_athletes, key=lambda entry: convert_time(entry[3]))

    if selected_sport == Sport.CROSS_COUNTRY: # Cross Country scoring system
        for i in range(len(varsity_athletes)):
            if len(varsity_athletes[i]) == 5: # If the athlete has already been scored as invalid, skip athlete
                continue
            varsity_athletes[i] += (i+1,)
    elif selected_sport == Sport.TRACK: # Track and Field scoring system: top 8 score, others score no points
        points = (10, 8, 6, 5, 4, 3, 2, 1)
        for i in range(len(varsity_athletes)):
            if i < 8:
                varsity_athletes[i] += (points[i],) # Scoring athletes
            else:
                varsity_athletes[i] += (-1,) # Loser athletes

    for athlete_entry in varsity_athletes:
        print(athlete_entry)

    return jsonify(varsity_athletes)

if __name__ == '__main__':
    app.run(debug=True)
